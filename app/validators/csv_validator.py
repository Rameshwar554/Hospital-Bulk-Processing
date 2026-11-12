import csv
import io

from fastapi import HTTPException

from app.core.config import MAX_HOSPITALS
from app.schemas.hospital import HospitalRow


def parse_csv(content: bytes) -> list[HospitalRow]:
    """Decode, normalize, and validate hospital rows from CSV bytes."""
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "CSV must use UTF-8 encoding.") from exc

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV is empty or missing a header row.")

    headers = [header.strip().lower() for header in reader.fieldnames if header]
    required = {"name", "address"}

    if not required.issubset(set(headers)):
        raise HTTPException(
            400,
            "CSV must contain name and address columns. phone is optional.",
        )

    if len(headers) != len(set(headers)):
        raise HTTPException(400, "CSV contains duplicate column names.")

    normalized_rows = []
    for line_number, raw_row in enumerate(reader, start=2):
        row = {
            (key.strip().lower() if key else ""): (value or "").strip()
            for key, value in raw_row.items()
        }

        if not any(row.values()):
            continue

        name = row.get("name", "")
        address = row.get("address", "")
        phone = row.get("phone") or None

        if not name or not address:
            raise HTTPException(
                400,
                f"Row {line_number}: name and address are required.",
            )

        normalized_rows.append(
            HospitalRow(name=name, address=address, phone=phone)
        )

    if not normalized_rows:
        raise HTTPException(400, "CSV does not contain any hospital records.")

    if len(normalized_rows) > MAX_HOSPITALS:
        raise HTTPException(
            400,
            f"Maximum {MAX_HOSPITALS} hospitals are allowed per CSV.",
        )

    return normalized_rows
