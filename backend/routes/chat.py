import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel
from backend.rag import ask as rag_ask, _extract_quantity, _extract_topic, _sanitize_filename
from backend.rag import _extract_search_keywords
from backend.rag import _query_llm, _build_butler_prompt, _detect_language, _load_personality
from backend.rag import _hybrid_search, _get_note_content, generate_quiz_batch, _CHUNK_SIZE
from backend.vector_store import search
from backend.evolution import (
    consolidate_from_conversation,
    save_connections,
    get_evolution_stats,
    background_evolution_loop,
    stop_background_evolution,
)
from backend.brain_manager import _EXPORT_CSS, _extract_title

logger = logging.getLogger("baul.chat")
router = APIRouter(prefix="/api")


class DownloadRequest(BaseModel):
    content: str
    format: str = "md"
    filename: str = ""

# Keep last conversation for evolution learning
_last_conversation: list = []


@router.on_event("startup")
async def start_evolution():
    asyncio.create_task(background_evolution_loop(interval_seconds=1800))
    logger.info("[Chat] Background evolution loop started")


@router.on_event("shutdown")
def stop_evolution():
    stop_background_evolution()
    logger.info("[Chat] Background evolution loop stopped")


@router.post("/search")
async def api_search(query: str = Form(""), k: int = Form(5)):
    results = await search(query, k)
    return {"results": results}


@router.post("/chat")
async def api_chat(message: str = Form(""), history: str = Form("")):
    global _last_conversation
    hist = json.loads(history) if history else None

    qty = _extract_quantity(message)
    lang = _detect_language(message)

    # ── Large quiz detection: delegate to batch generator ──
    if qty > _CHUNK_SIZE:
        # Extract clean topic for display AND separate keywords for brain search
        topic_raw = _extract_topic(message)       # sanitized filename version
        topic_keywords = _extract_search_keywords(message)  # clean search terms
        try:
            # Very generous timeout for batch generation (chunks × 65s each, covers fallback chain)
            batch_timeout = max(180.0, qty / _CHUNK_SIZE * 65.0)
            quiz_content = await asyncio.wait_for(
                generate_quiz_batch(topic_keywords, qty, lang, search_query=topic_keywords),
                timeout=batch_timeout,
            )

            # Build a downloadable quiz result
            # Clean filename: use keywords minus quantity, prefix with "Quiz-"
            topic_clean = _sanitize_filename(topic_keywords, "quiz")
            dl_topic = f"Quiz-{topic_clean}"  # frontend adds "EAgis-" → EAgis-Quiz-Algoritmos-C.md
            q_count = sum(1 for line in quiz_content.split("\n") if "**Respuesta correcta:**" in line or "**Respuesta:**" in line or "Correct answer:" in line or "Answer:" in line)
            q_count = max(1, min(q_count, qty))

            # Show just the summary in chat, full content goes to download
            summary = (
                f"# Quiz generado: {topic_keywords.title()}\n\n"
                f"**{q_count} preguntas de {qty}** generadas exitosamente.\n\n"
                f"Usá los botones ⬇️ .md o ⬇️ .pdf abajo para descargar.\n\n"
                f"---\n\n"
                f"{quiz_content[:500]}\n..."
            )

            result = {
                "answer": summary,
                "sources": [],
                "connections": [],
                "web_search_used": False,
                "suggest_save": False,
                "is_quiz": True,
                "topic": dl_topic,  # frontend: makeFilename → "EAgis-Quiz-Algoritmos-C.md"
                "full_content": quiz_content,  # full quiz for download
                "personality": {
                    "interactions": 0,
                    "traits": [],
                    "topics": [],
                },
            }
        except asyncio.TimeoutError:
            result = {
                "answer": (
                    f"*(El cuestionario de {qty} preguntas es demasiado extenso incluso "
                    f"dividido en partes. Probá con menos preguntas o un tema más específico.)*"
                    if lang == "es" else
                    f"*(The {qty}-question quiz is too large even when split. "
                    f"Try fewer questions or a more specific topic.)*"
                ),
                "sources": [],
                "connections": [],
                "web_search_used": False,
                "suggest_save": False,
            }
        except Exception as e:
            logger.error(f"[Chat] Batch quiz error: {e}")
            result = {
                "answer": (
                    f"*Ocurrió un error generando el cuestionario. Intentá de nuevo.*" if lang == "es"
                    else f"*An error occurred generating the quiz. Try again.*"
                ),
                "sources": [],
                "connections": [],
                "web_search_used": False,
                "suggest_save": False,
            }

        # Skip learning for batch quizzes (content is too large to usefully consolidate)
        return result

    # ── Normal chat / small quiz path ──
    timeout = max(15.0, min(15 + qty * 0.8, 180.0)) if qty > 0 else 5.0
    k_val = 3 if qty > 20 else 5
    try:
        result = await asyncio.wait_for(rag_ask(message, hist, k=k_val), timeout=timeout)
    except asyncio.TimeoutError:
        result = {
            "answer": "(EAgis está procesando una respuesta extensa) Parece que el contenido que pedís requiere más tiempo de generación. Probá con menos preguntas o intentá de nuevo." if lang == "es" else "(Respuesta rápida local — EAgis está meditando) No tengo una respuesta completa, pero revisá tus notas manualmente.",
            "sources": [],
            "connections": [],
            "web_search_used": False,
            "suggest_save": False,
        }

    # --- Autonomous learning: consolidate from conversation ---
    if hist:
        _last_conversation = hist[-6:] + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": result.get("answer", "")},
        ]
        # Fire-and-forget consolidation (non-blocking)
        asyncio.create_task(_learn_from_conversation())

    return result


async def _learn_from_conversation():
    """Non-blocking evolution trigger."""
    global _last_conversation
    try:
        draft = await consolidate_from_conversation(_last_conversation)
        if draft:
            logger.info(f"[Evolution] Created draft note from conversation: {draft}")
    except Exception as e:
        logger.warning(f"[Evolution] Consolidation skipped: {e}")


@router.get("/evolution/stats")
async def evolution_stats():
    return get_evolution_stats()


@router.post("/chat/download")
async def api_chat_download(req: DownloadRequest):
    """Generate a downloadable file from AI-generated content."""
    content = req.content
    fmt = req.format.lower()
    name = req.filename.strip() or "EAgis-response"

    if fmt == "md":
        safe_name = name if name.endswith(".md") else f"{name}.md"
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )

    elif fmt == "pdf":
        try:
            import markdown
            html_body = markdown.markdown(content, extensions=["fenced_code", "tables"])
            title = _extract_title(content) or name
            footer = f'<div class="footer">Generado por EAgis &mdash; {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>'
            styled = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>{title}</title><style>{_EXPORT_CSS}</style></head><body>{html_body}{footer}</body></html>"""
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=styled).write_pdf()
            except (ImportError, OSError):
                # Fallback: return styled HTML for browser print-to-PDF
                return Response(
                    content=styled,
                    media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f'inline; filename="{name}.html"'},
                )
            safe_name = name if name.endswith(".pdf") else f"{name}.pdf"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
            )
        except (ImportError, OSError):
            return {"error": "PDF generation requires weasyprint + markdown. Try .md format instead."}, 400

    return {"error": f"Formato no soportado: {fmt}. Usá 'md' o 'pdf'."}, 400
