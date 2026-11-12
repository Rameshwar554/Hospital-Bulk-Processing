from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.core.config import MAX_FILE_BYTES
from app.services.bulk_processor import batch_results, process_batch
from app.validators.csv_validator import parse_csv

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "index.html"


async def home():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


async def health():
    return {"status": "ok"}


async def validate_csv(file: UploadFile):
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 1 MB upload limit.")

    rows = parse_csv(content)
    return {
        "valid": True,
        "total_hospitals": len(rows),
        "columns": ["name", "address", "phone"],
    }


async def bulk_create_hospitals(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")

    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 1 MB upload limit.")

    rows = parse_csv(content)
    return await process_batch(rows)


async def get_batch_status(batch_id: str):
    result = batch_results.get(batch_id)
    if not result:
        raise HTTPException(404, "Batch not found in this application instance.")
    return result
