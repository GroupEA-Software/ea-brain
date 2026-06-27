"""API v2 chat route — uses ChatService with concurrent LLM racing and batch quiz support."""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel

from backend.application.app import ensure_built
from backend.application.chat import ChatService
from backend.application.quiz import QuizService, CHUNK_SIZE
from backend.evolution import consolidate_from_conversation
from backend.brain_manager import _EXPORT_CSS, _extract_title
from backend.infrastructure.logger import get_logger

logger = get_logger("routes.v2.chat")
router = APIRouter(prefix="/api/v2")

CHUNK_SIZE = 25  # same as rag._CHUNK_SIZE

class DownloadRequest(BaseModel):
    content: str
    format: str = "md"
    filename: str = ""

_last_conversation: list = []
_chat_lock = asyncio.Lock()

@router.post("/chat")
async def api_chat_v2(message: str = Form(""), history: str = Form("")):
    global _last_conversation
    hist = json.loads(history) if history else None

    # Resolve services from container
    c = ensure_built()
    chat_svc = c.resolve(ChatService)
    quiz_svc = c.resolve(QuizService)

    qty = chat_svc._extract_quantity(message)  # reuse existing logic
    lang = chat_svc._detect_language(message)

    # ── Large quiz: delegate to QuizService ──
    if qty > CHUNK_SIZE:
        # Extract topic keywords using the method (or just use message as topic)
        topic = message[:100].strip()
        try:
            batch_timeout = max(180.0, qty / CHUNK_SIZE * 65.0)
            quiz_content = await asyncio.wait_for(
                quiz_svc.generate(topic, qty, lang),
                timeout=batch_timeout,
            )

            q_count = sum(1 for line in quiz_content.split("\n") 
                         if "**Respuesta correcta:**" in line or "**Respuesta:**" in line 
                         or "Correct answer:" in line or "Answer:" in line)
            q_count = max(1, min(q_count, qty))

            dl_topic = topic.strip().replace(" ", "-")[:50]
            summary = (
                f"# Quiz generado: {topic.strip().title()}\n\n"
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
                "topic": dl_topic,
                "full_content": quiz_content,
                "personality": {"interactions": 0, "traits": [], "topics": []},
            }
        except asyncio.TimeoutError:
            result = {
                "answer": (f"*(El cuestionario de {qty} preguntas es demasiado extenso incluso "
                          f"dividido en partes. Probá con menos preguntas o un tema más específico.)*"
                          if lang == "es" else
                          f"*(The {qty}-question quiz is too large even when split. "
                          f"Try fewer questions or a more specific topic.)*"),
                "sources": [], "connections": [],
                "web_search_used": False, "suggest_save": False,
            }
        except Exception as e:
            logger.error("V2 batch quiz error: %s", e)
            result = {
                "answer": (f"*Ocurrió un error generando el cuestionario. Intentá de nuevo.*" if lang == "es"
                          else f"*An error occurred generating the quiz. Try again.*"),
                "sources": [], "connections": [],
                "web_search_used": False, "suggest_save": False,
            }
        return result

    # ── Normal chat / small quiz path ──
    timeout = max(15.0, min(15 + qty * 0.8, 180.0)) if qty > 0 else 15.0
    try:
        result = await asyncio.wait_for(
            chat_svc.answer(message, hist),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        result = {
            "answer": ("(EAgis está procesando una respuesta extensa) Parece que el contenido "
                      "que pedís requiere más tiempo de generación. Probá con menos preguntas o "
                      "intentá de nuevo." if lang == "es" else
                      "(Quick local response) I couldn't generate a complete answer in time. "
                      "Try a simpler query."),
            "sources": [], "connections": [],
            "web_search_used": False, "suggest_save": False,
        }

    # Add frontend-required fields
    result.setdefault("web_search_used", False)
    result.setdefault("suggest_save", False)

    # ── Autonomous learning ──
    if hist:
        async with _chat_lock:
            _last_conversation = hist[-6:] + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": result.get("answer", "")},
            ]
        asyncio.create_task(_learn_from_conversation())

    return result


async def _learn_from_conversation():
    """Non-blocking evolution trigger."""
    global _last_conversation
    async with _chat_lock:
        try:
            draft = await consolidate_from_conversation(_last_conversation)
            if draft:
                logger.info("V2 evolution draft: %s", draft)
        except Exception as e:
            logger.warning("V2 evolution skipped: %s", e)


@router.post("/chat/download")
async def api_chat_download_v2(req: DownloadRequest):
    """Generate downloadable file from AI content (.md or .pdf)."""
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
