import os
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

from backend.config import BRAIN_NOTES, BRAIN_INBOX, GEMINI_API_KEY, GEMINI_MODEL
from backend.vector_store import add_document

_executor = ThreadPoolExecutor(max_workers=1)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma", ".aac", ".webm"}


CHUNK_DURATION_SEC = 1500  # 25 min per chunk (under Gemini limits)

def _compress_audio(input_path: str, output_path: str, max_size_mb: int = 20) -> str:
    """Compress audio to target max size using ffmpeg if available."""
    try:
        import subprocess as sp
        target_bitrate = "32k"
        size_mb = os.path.getsize(input_path) / (1024 * 1024)
        if size_mb > 50:
            target_bitrate = "24k"
        elif size_mb > 100:
            target_bitrate = "16k"
        sp.run(
            ["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", "16000",
             "-b:a", target_bitrate, "-max_size", f"{max_size_mb}M", output_path],
            capture_output=True, timeout=120,
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except Exception:
        pass
    return input_path


def _get_audio_duration_ffmpeg(input_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        import subprocess as sp, json
        result = sp.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", input_path],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except Exception:
        pass
    return 0.0


def _split_audio(input_path: str, chunk_sec: int = CHUNK_DURATION_SEC) -> list:
    """Split audio into numbered chunks using ffmpeg. Returns list of chunk paths."""
    chunks = []
    base = input_path.rsplit(".", 1)[0]
    ext = input_path.rsplit(".", 1)[-1] if "." in input_path else "mp3"
    out_pattern = os.path.join(os.path.dirname(input_path), f"{os.path.basename(base)}_chunk_%03d.{ext}")
    try:
        import subprocess as sp
        sp.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-f", "segment", "-segment_time", str(chunk_sec),
             "-c", "copy",
             "-reset_timestamps", "1",
             out_pattern],
            capture_output=True, timeout=86400,
        )
        # Collect generated chunks
        for f in sorted(os.listdir(os.path.dirname(input_path))):
            if f.startswith(os.path.basename(base) + "_chunk_") and f.endswith("." + ext):
                chunks.append(os.path.join(os.path.dirname(input_path), f))
    except Exception as e:
        print(f"[Baul] Audio split error: {e}")
    return chunks


def _transcribe_chunked(audio_path: str, language: str = None) -> Optional[dict]:
    """Transcribe long audio by splitting into chunks and transcribing each."""
    duration = _get_audio_duration_ffmpeg(audio_path)
    if duration <= 0:
        duration = 60 * 60  # assume 1h if detection fails

    if duration <= CHUNK_DURATION_SEC:
        return _transcribe_gemini(audio_path, language)

    print(f"[Baul] Audio duration {duration:.0f}s > {CHUNK_DURATION_SEC}s, splitting into chunks...")
    chunks = _split_audio(audio_path)
    if not chunks:
        print(f"[Baul] Split failed, trying full file anyway...")
        return _transcribe_gemini(audio_path, language)

    all_segments = []
    total_dur = 0.0
    full_text_parts = []

    for i, chunk_path in enumerate(chunks):
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024) if os.path.exists(chunk_path) else 0
        print(f"[Baul] Transcribing chunk {i+1}/{len(chunks)} ({chunk_size_mb:.1f}MB)...")
        try:
            raw = _transcribe_gemini(chunk_path, language)
            if raw and raw.get("full_text"):
                offset = total_dur
                for seg in raw.get("segments", []):
                    seg["start"] += offset
                    seg["end"] += offset
                    all_segments.append(seg)
                total_dur += raw["duration"]
                full_text_parts.append(
                    f"[Parte {i+1} / {len(chunks)}]\n\n{raw['full_text']}\n"
                )
            else:
                full_text_parts.append(f"[Parte {i+1} / {len(chunks)}]\n\n*[transcripci\u00f3n no disponible]*\n")
        except Exception as e:
            print(f"[Baul] Chunk {i+1} fallo: {e}")
            full_text_parts.append(f"[Parte {i+1} / {len(chunks)}]\n\n*[error: {e}]*\n")
        finally:
            try:
                os.unlink(chunk_path)
            except Exception:
                pass

    if not all_segments and not full_text_parts:
        return None

    return {
        "language": language or "auto",
        "duration": total_dur or duration,
        "segments": all_segments or [{"start": 0, "end": duration, "text": " ".join(full_text_parts)}],
        "full_text": "\n\n".join(full_text_parts),
    }


GEMINI_MODELS_FOR_AUDIO = [
    GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-3.0-flash",
    "gemini-3.0-flash-lite",
    "gemini-3.0-pro",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-pro",
]


def _transcribe_gemini(audio_path: str, language: str = None) -> Optional[dict]:
    """Transcribe using Gemini models (2.5 -> 3.0 -> 3.5 families)."""
    if not GEMINI_API_KEY:
        return None

    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    compressed = audio_path
    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if size_mb > 15:
        compressed_path = audio_path + ".compressed.mp3"
        compressed = _compress_audio(audio_path, compressed_path, max_size_mb=15)
        if compressed == audio_path:
            compressed_path = audio_path

    file_ref = genai.upload_file(compressed)

    prompt = "Transcribe this audio word for word. Return ONLY the transcription text, no additional commentary."
    if language:
        prompt = f"Transcribe this {language} audio word for word. Return ONLY the transcription, no commentary."

    for model_name in GEMINI_MODELS_FOR_AUDIO:
        try:
            model = genai.GenerativeModel(model_name)
            result = model.generate_content([prompt, file_ref])
            text = result.text.strip() if result.text else ""
            if not text:
                continue

            segments_raw = text.split("\n\n")
            segments = []
            total_dur = 0
            for seg_text in segments_raw:
                seg_text = seg_text.strip()
                if seg_text:
                    segments.append({
                        "start": total_dur,
                        "end": total_dur + len(seg_text.split()) * 0.3,
                        "text": seg_text,
                    })
                    total_dur += len(seg_text.split()) * 0.3

            return {
                "language": language or "auto",
                "duration": total_dur,
                "segments": segments,
                "full_text": " ".join(s["text"] for s in segments),
            }
        except Exception as e:
            err = str(e).lower()
            if "not found" in err or "not supported" in err or "not available" in err:
                continue
            if "429" in str(e) or "quota" in err or "rate" in err or "resource exhausted" in err:
                continue
            print(f"[Baul] Gemini {model_name} fallo: {e}")
            continue
    return None


def _segment_by_topic(segments: List[dict], min_gap: float = 3.0) -> List[dict]:
    if not segments:
        return []
    sections = []
    current = {"start": segments[0]["start"], "texts": [segments[0]]}
    total_text = segments[0]["text"]
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i - 1]["end"]
        if gap > min_gap and len(current["texts"]) > 0:
            current["end"] = segments[i - 1]["end"]
            current["text"] = " ".join(s["text"] for s in current["texts"])
            current["duration"] = current["end"] - current["start"]
            sections.append(current)
            current = {"start": segments[i]["start"], "texts": [segments[i]]}
        else:
            current["texts"].append(segments[i])
        total_text += " " + segments[i]["text"]
    if current["texts"]:
        current["end"] = segments[-1]["end"]
        current["text"] = " ".join(s["text"] for s in current["texts"])
        current["duration"] = current["end"] - current["start"]
        sections.append(current)
    return sections


def _extract_key_terms(text: str, top_n: int = 15) -> List[str]:
    import string
    stop_words = {
        "que", "es", "el", "la", "los", "las", "un", "una", "y", "e", "o", "a",
        "de", "del", "en", "con", "por", "para", "se", "su", "no", "lo", "como",
        "m\u00e1s", "pero", "sus", "le", "ya", "este", "entre", "porque", "cuando",
        "todo", "tambi\u00e9n", "fue", "era", "muy", "sin", "sobre", "ser", "tiene",
        "son", "dos", "hay", "cada", "parte", "donde", "cual", "the", "and",
        "that", "this", "with", "from", "they", "have", "been", "were", "what",
        "which", "their", "about", "would", "could", "there", "these", "into",
        "than", "then", "also", "such", "some", "other", "more", "very",
    }
    words = re.findall(r"[a-zA-Z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc]+", text.lower())
    words = [w for w in words if len(w) > 3 and w not in stop_words]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:top_n]]


def _format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _build_local_study_notes(raw: dict, filename: str) -> str:
    title = Path(filename).stem.replace("-", " ").replace("_", " ").title()
    duration_min = raw["duration"] / 60
    segments = raw["segments"]
    full_text = raw["full_text"]

    sections = _segment_by_topic(segments, min_gap=3.0)
    key_terms = _extract_key_terms(full_text)

    md = f"""# {title}

> Transcripci\u00f3n generada por **Baul Transcriber**
> Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Duraci\u00f3n: {int(duration_min)} min {int(raw['duration'] % 60)} s
> Idioma detectado: {raw['language'].upper()}
> Palabras: {len(full_text.split())}

---

## Resumen Ejecutivo

Esta transcripci\u00f3n corresponde a **{title}**. A continuaci\u00f3n se presenta el contenido
organizado en {len(sections)} secciones tem\u00e1ticas con un total de {len(segments)} segmentos.

---

## Conceptos Clave

| Concepto | Descripci\u00f3n |
|----------|-------------|
"""
    for term in key_terms[:10]:
        context_snippets = []
        for seg in segments:
            if term.lower() in seg["text"].lower():
                context_snippets.append(seg["text"][:100])
                if len(context_snippets) >= 2:
                    break
        context = context_snippets[0] if context_snippets else "(t\u00e9rmino clave)"
        md += f"| **{term.title()}** | {context}... |\n"

    md += f"""
---

## Transcripci\u00f3n Completa

"""

    for i, section in enumerate(sections, 1):
        ts = _format_timestamp(section["start"])
        section_text = section["text"]
        first_sentences = re.split(r'[.!?]', section_text[:200])
        section_title = first_sentences[0].strip() if first_sentences else f"Secci\u00f3n {i}"
        if len(section_title) > 60:
            section_title = section_title[:60] + "..."

        md += f"""### {i}. {section_title}

*[{ts}]*

{section_text}

"""

    md += f"""---

## Glosario

| T\u00e9rmino | Contexto |
|---------|----------|
"""
    for term in key_terms[:15]:
        for seg in segments:
            if term.lower() in seg["text"].lower():
                snippet = seg["text"].replace(term, f"**{term}**", 1)[:120]
                md += f"| **{term.title()}** | {snippet}... |\n"
                break

    md += f"""
---

## Preguntas de Estudio

1. \u00bfCu\u00e1les son los conceptos principales presentados en **{title}**?
2. \u00bfC\u00f3mo se relacionan los t\u00e9rminos clave entre s\u00ed?
3. \u00bfQu\u00e9 ejemplos se mencionan y c\u00f3mo ilustran los conceptos?
4. \u00bfQu\u00e9 conclusiones se pueden extraer del contenido?

---

*Transcripci\u00f3n generada autom\u00e1ticamente por el Agente Transcriber de Baul.*
*Revisa y complementa el contenido para enriquecer tu cerebro.*
"""
    return md


def _query_llm_enhance(transcript: str, title: str, duration: float, language: str) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None
    prompt = f"""Eres un profesor experto transformando transcripciones de clases en notas de estudio excepcionales.

## Transcripci\u00f3n original
- T\u00edtulo: {title}
- Duraci\u00f3n: {int(duration // 60)} min {int(duration % 60)} s
- Idioma: {language.upper()}

## Transcripci\u00f3n
{transcript[:12000]}

## Instrucciones
Transforma esta transcripci\u00f3n en notas de estudio COMPLETAS y ESTRUCTURADAS en Markdown.
Debe sentirte como si un profesor estuviera ense\u00f1\u00e1ndote, NO como un punteo simple.

Formato requerido:
1. **T\u00edtulo** descriptivo
2. **Metadatos**: fecha, duraci\u00f3n, idioma
3. **Resumen Ejecutivo**: s\u00edntesis de 3-5 p\u00e1rrafos explicando de qu\u00e9 trata
4. **\u00cdndice de contenidos** con tiempos
5. **Desarrollo completo**: cada secci\u00f3n debe tener un t\u00edtulo descriptivo, incluir marca de tiempo [MM:SS], explicar los conceptos con detalle, no solo transcribir
6. **Mapa conceptual**: relaciones entre ideas principales
7. **Glosario**: t\u00e9rminos clave con definiciones extra\u00eddas del contexto
8. **Preguntas de estudio**: 5-8 preguntas que realmente hagan pensar
9. **Conexiones**: qu\u00e9 otros temas podr\u00edan relacionarse

Estilo: profundo, claro, did\u00e1ctico. Desarrolla las ideas en p\u00e1rrafos completos.
Usa [[wikilinks]] para conectar con otros conceptos cuando sea natural."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        return resp.text.strip() if resp.text else None
    except Exception as e:
        return None


async def transcribe_audio(filename: str, language: str = None) -> Optional[dict]:
    """Transcribe an audio file using Gemini (2.5/3.0/3.5 families)."""
    audio_path = BRAIN_INBOX / filename
    if not audio_path.exists():
        return None

    try:
        loop = asyncio.get_event_loop()

        raw = await loop.run_in_executor(_executor, _transcribe_chunked, str(audio_path), language)

        title_base = Path(filename).stem
        safe_title = re.sub(r"[^a-zA-Z0-9\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc\s-]", "", title_base).strip()[:80]
        md_filename = f"audios/{safe_title.lower().replace(' ', '-')[:60]}.md"
        dst = BRAIN_NOTES / md_filename
        dst.parent.mkdir(parents=True, exist_ok=True)

        enhanced = None
        full_text = raw["full_text"]
        if len(full_text) > 12000:
            full_text_for_llm = full_text[:12000] + f"\n\n[... la transcripci\u00f3n completa tiene {len(full_text)} caracteres, se muestran los primeros 12000]"
        else:
            full_text_for_llm = full_text
        enhanced = await loop.run_in_executor(
            _executor,
            _query_llm_enhance,
            full_text_for_llm,
            safe_title,
            raw["duration"],
            raw["language"],
        )

        if enhanced:
            md_content = enhanced
        else:
            md_content = _build_local_study_notes(raw, filename)
        loop2 = asyncio.get_event_loop()
        await loop2.run_in_executor(None, lambda: dst.write_text(md_content, encoding="utf-8"))

        await add_document(md_filename, md_content)
        audio_path.unlink()

        return {
            "filename": md_filename,
            "title": safe_title,
            "language": raw["language"],
            "duration": raw["duration"],
            "words": len(raw["full_text"].split()),
            "segments": len(raw["segments"]),
            "enhanced": enhanced is not None,
        }

    except Exception as e:
        raise Exception(f"Transcripcion fallo: {e}")


async def transcribe_all_pending() -> list:
    results = []
    for f in sorted(BRAIN_INBOX.iterdir()):
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
            try:
                result = await transcribe_audio(f.name)
                if result:
                    results.append(result)
            except Exception as e:
                results.append({"file": f.name, "error": str(e)})
    return results


def is_audio_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in AUDIO_EXTENSIONS
