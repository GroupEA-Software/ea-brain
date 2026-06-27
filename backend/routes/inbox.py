from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from backend.config import BRAIN_INBOX, BRAIN_NOTES
from backend.brain_manager import get_inbox_files
from backend.converter import convert_file, convert_all_inbox, _is_likely_image_bytes, _convert_image
from backend.transcriber import transcribe_audio, transcribe_all_pending, is_audio_file
from backend.vector_store import add_document

router = APIRouter(prefix="/api")


@router.get("/inbox")
async def api_inbox():
    return await get_inbox_files()


@router.post("/inbox/upload")
async def api_upload(file: UploadFile = File(...), auto: bool = False, folder: str = ""):
    dest = BRAIN_INBOX / file.filename
    content = await file.read()
    with open(str(dest), "wb") as f:
        f.write(content)
    ext = Path(file.filename).suffix.lower()
    if auto or ext == ".pdf" or ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        try:
            if is_audio_file(file.filename):
                result = await transcribe_audio(file.filename)
                if result:
                    return {"filename": file.filename, "status": "transcribed", "result": result}
            else:
                try:
                    result = await convert_file(file.filename, folder=folder)
                    if result:
                        await add_document(result, "")
                        return {"filename": file.filename, "status": "converted", "result": result}
                except Exception:
                    pass
                # Ultimate fallback: try OCR on anything
                try:
                    from backend.converter import IMAGE_EXTENSIONS
                    img_folder = folder if folder else "img"
                    img_dst = BRAIN_NOTES / img_folder / (dest.stem + ".md")
                    img_dst.parent.mkdir(parents=True, exist_ok=True)
                    ocr_result = await _convert_image(dest, img_dst, file.filename, subfolder=folder)
                    if ocr_result:
                        await add_document(ocr_result, "")
                        return {"filename": file.filename, "status": "converted", "result": ocr_result}
                except Exception:
                    pass
        except Exception as e:
            print(f"[Baul] Upload error for {file.filename}: {e}")
            return {"filename": file.filename, "status": "uploaded", "auto_convert_error": str(e)}
    return {"filename": file.filename, "status": "uploaded"}


@router.post("/convert")
async def api_convert(filename: str = "", folder: str = ""):
    if filename:
        if is_audio_file(filename):
            result = await transcribe_audio(filename)
            if result:
                return {"transcribed": [result]}
            return {"error": "No se pudo transcribir el audio"}, 400
        conv = None
        try:
            conv = await convert_file(filename, folder=folder)
        except Exception:
            conv = None
        if not conv:
            try:
                src = BRAIN_INBOX / filename
                from backend.converter import IMAGE_EXTENSIONS
                img_folder = folder if folder else "img"
                dst = BRAIN_NOTES / img_folder / (src.stem + ".md")
                dst.parent.mkdir(parents=True, exist_ok=True)
                conv = await _convert_image(src, dst, filename, subfolder=folder)
            except Exception:
                pass
        if conv:
            await add_document(conv, "")
            return {"converted": [conv]}
        return {"error": "No se pudo convertir"}, 400
    results = await convert_all_inbox()
    for r in results:
        if isinstance(r, str):
            await add_document(r, "")
    audio_results = await transcribe_all_pending()
    return {"converted": results, "transcribed": audio_results}


@router.post("/convert-all")
async def api_convert_all():
    results = await convert_all_inbox()
    for r in results:
        if isinstance(r, str):
            await add_document(r, "")
    audio_results = await transcribe_all_pending()
    return {"converted": results, "transcribed": audio_results}


@router.post("/transcribe")
async def api_transcribe(filename: str = "", language: str = ""):
    if not filename:
        audio_results = await transcribe_all_pending()
        return {"transcribed": audio_results}
    lang = language if language else None
    result = await transcribe_audio(filename, lang)
    if result:
        return {"transcribed": [result]}
    return {"error": "No se pudo transcribir"}, 400


@router.post("/transcribe-upload")
async def api_transcribe_upload(file: UploadFile = File(...), language: str = ""):
    dest = BRAIN_INBOX / file.filename
    content = await file.read()
    with open(str(dest), "wb") as f:
        f.write(content)
    if is_audio_file(file.filename):
        lang = language if language else None
        result = await transcribe_audio(file.filename, lang)
        return {"transcribed": [result]} if result else {"error": "Transcripcion fallo"}, 400
    return {"filename": file.filename, "status": "uploaded"}
