from fastapi import APIRouter
from fastapi.responses import Response
from backend.config import BRAIN_NOTES
from backend.brain_manager import export_note_md, export_note_pdf, export_note_html, export_vault_zip

router = APIRouter(prefix="/api")


@router.get("/export/{filename:path}")
async def api_export_note(filename: str, format: str = "md"):
    path = BRAIN_NOTES / filename
    if not path.exists():
        return {"error": "Nota no encontrada"}, 404

    if format == "md":
        content = await export_note_md(filename)
        if content is None:
            return {"error": "No se pudo exportar"}, 400
        return Response(content=content, media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{path.name}"'})

    elif format == "pdf":
        pdf_bytes = await export_note_pdf(filename)
        if pdf_bytes:
            return Response(content=pdf_bytes, media_type="application/pdf",
                            headers={"Content-Disposition": f'attachment; filename="{path.stem}.pdf"'})
        html = await export_note_html(filename)
        if html:
            return Response(content=html, media_type="text/html",
                            headers={"Content-Disposition": f'inline; filename="{path.stem}.html"'})
        return {"error": "No se pudo generar PDF (instala markdown + weasyprint)"}, 400

    elif format == "html":
        html = await export_note_html(filename)
        if html:
            return Response(content=html, media_type="text/html",
                            headers={"Content-Disposition": f'inline; filename="{path.stem}.html"'})
        return {"error": "No se pudo generar HTML"}, 400

    return {"error": f"Formato no soportado: {format}"}, 400


@router.get("/export-vault")
async def api_export_vault():
    zip_bytes = await export_vault_zip()
    if zip_bytes:
        return Response(content=zip_bytes, media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="baul-vault.zip"'})
    return {"error": "No se pudo exportar la boveda"}, 400
