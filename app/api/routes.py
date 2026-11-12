from fastapi import APIRouter, File, UploadFile
from fastapi.responses import HTMLResponse

from app.api import handlers

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return await handlers.home()


@router.get("/health")
async def health():
    return await handlers.health()


@router.post("/hospitals/validate")
async def validate_csv(file: UploadFile = File(...)):
    return await handlers.validate_csv(file)


@router.post("/hospitals/bulk")
async def bulk_create_hospitals(file: UploadFile = File(...)):
    return await handlers.bulk_create_hospitals(file)


@router.get("/hospitals/bulk/{batch_id}")
async def get_batch_status(batch_id: str):
    return await handlers.get_batch_status(batch_id)
