from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Paribus Hospital Bulk Processing API",
    description="Upload a CSV and create hospitals through the supplied Hospital Directory API.",
    version="1.0.0",
)

app.include_router(router)

# Backward-compatible exports for the existing tests and imports.
from app.schemas.hospital import HospitalRow  # noqa: E402
from app.validators.csv_validator import parse_csv  # noqa: E402
from app.services.bulk_processor import process_batch, batch_results  # noqa: E402
