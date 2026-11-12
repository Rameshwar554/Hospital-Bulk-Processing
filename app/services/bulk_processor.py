import asyncio
import time
import uuid
from typing import Any

import httpx

from app.core.config import (
    CONNECT_TIMEOUT_SECONDS,
    DIRECTORY_API_URL,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_TIMEOUT_SECONDS,
)
from app.schemas.hospital import HospitalRow

# In-memory storage is retained to match the current assignment implementation.
batch_results: dict[str, dict[str, Any]] = {}


async def create_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    batch_id: str,
    row_number: int,
    hospital: HospitalRow,
) -> dict[str, Any]:
    payload = {
        "name": hospital.name,
        "address": hospital.address,
        "creation_batch_id": batch_id,
    }
    if hospital.phone:
        payload["phone"] = hospital.phone

    async with semaphore:
        try:
            response = await client.post("/hospitals/", json=payload)
            response.raise_for_status()
            data = response.json()
            return {
                "row": row_number,
                "hospital_id": data.get("id"),
                "name": hospital.name,
                "status": "created",
                "error": None,
            }
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "row": row_number,
                "hospital_id": None,
                "name": hospital.name,
                "status": "failed",
                "error": str(exc),
            }


async def process_batch(
    rows: list[HospitalRow],
    client_factory=httpx.AsyncClient,
) -> dict[str, Any]:
    batch_id = str(uuid.uuid4())
    started = time.perf_counter()

    timeout = httpx.Timeout(
        REQUEST_TIMEOUT_SECONDS,
        connect=CONNECT_TIMEOUT_SECONDS,
    )
    limits = httpx.Limits(max_connections=MAX_CONCURRENT_REQUESTS)

    async with client_factory(
        base_url=DIRECTORY_API_URL,
        timeout=timeout,
        limits=limits,
    ) as client:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        results = await asyncio.gather(
            *[
                create_one(client, semaphore, batch_id, index, hospital)
                for index, hospital in enumerate(rows, start=1)
            ]
        )

        failed = sum(item["status"] == "failed" for item in results)
        activated = False
        activation_error = None

        # Activate only when every hospital creation succeeds.
        if failed == 0:
            try:
                response = await client.patch(
                    f"/hospitals/batch/{batch_id}/activate"
                )
                response.raise_for_status()
                activated = True
                for item in results:
                    item["status"] = "created_and_activated"
            except httpx.HTTPError as exc:
                activation_error = str(exc)
                for item in results:
                    item["status"] = "created_activation_failed"
                    item["error"] = activation_error

    elapsed = round(time.perf_counter() - started, 3)
    processed = len(results) - failed

    response_data = {
        "batch_id": batch_id,
        "total_hospitals": len(rows),
        "processed_hospitals": processed,
        "failed_hospitals": failed,
        "processing_time_seconds": elapsed,
        "batch_activated": activated,
        "status": (
            "completed"
            if activated
            else "partially_failed"
            if failed
            else "activation_failed"
        ),
        "activation_error": activation_error,
        "hospitals": results,
    }

    batch_results[batch_id] = response_data
    return response_data
