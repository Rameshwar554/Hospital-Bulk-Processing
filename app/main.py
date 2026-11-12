import asyncio
import csv
import io
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DIRECTORY_API_URL = os.getenv(
    "HOSPITAL_DIRECTORY_API_URL",
    "https://hospital-directory.onrender.com"
).rstrip("/")
MAX_HOSPITALS = 20
MAX_FILE_BYTES = 1024 * 1024
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))

app = FastAPI(
    title="Paribus Hospital Bulk Processing API",
    description="Upload a CSV and create hospitals through the supplied Hospital Directory API.",
    version="1.0.0",
)

# In-memory result store, as permitted by the assignment.
batch_results: dict[str, dict[str, Any]] = {}


class HospitalRow(BaseModel):
    name: str
    address: str
    phone: str | None = None


def parse_csv(content: bytes) -> list[HospitalRow]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "CSV must use UTF-8 encoding.") from exc

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV is empty or missing a header row.")

    headers = [h.strip().lower() for h in reader.fieldnames if h]
    required = {"name", "address"}
    if not required.issubset(set(headers)):
        raise HTTPException(
            400,
            "CSV must contain name and address columns. phone is optional."
        )
    if len(headers) != len(set(headers)):
        raise HTTPException(400, "CSV contains duplicate column names.")

    # Normalize header names while preserving the original CSV values.
    normalized_rows = []
    for line_number, raw in enumerate(reader, start=2):
        row = {
            (key.strip().lower() if key else ""): (value or "").strip()
            for key, value in raw.items()
        }
        if not any(row.values()):
            continue
        name = row.get("name", "")
        address = row.get("address", "")
        phone = row.get("phone") or None
        if not name or not address:
            raise HTTPException(
                400,
                f"Row {line_number}: name and address are required."
            )
        normalized_rows.append(HospitalRow(name=name, address=address, phone=phone))

    if not normalized_rows:
        raise HTTPException(400, "CSV does not contain any hospital records.")
    if len(normalized_rows) > MAX_HOSPITALS:
        raise HTTPException(
            400, f"Maximum {MAX_HOSPITALS} hospitals are allowed per CSV."
        )
    return normalized_rows


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
    rows: list[HospitalRow], client_factory=httpx.AsyncClient
) -> dict[str, Any]:
    batch_id = str(uuid.uuid4())
    started = time.perf_counter()
    timeout = httpx.Timeout(30.0, connect=10.0)
    limits = httpx.Limits(max_connections=MAX_CONCURRENT_REQUESTS)

    async with client_factory(
        base_url=DIRECTORY_API_URL,
        timeout=timeout,
        limits=limits,
    ) as client:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        results = await asyncio.gather(*[
            create_one(client, semaphore, batch_id, index, hospital)
            for index, hospital in enumerate(rows, start=1)
        ])

        failed = sum(item["status"] == "failed" for item in results)
        activated = False
        activation_error = None

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
            "completed" if activated
            else "partially_failed" if failed
            else "activation_failed"
        ),
        "activation_error": activation_error,
        "hospitals": results,
    }
    batch_results[batch_id] = response_data
    return response_data


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return HTMLResponse("""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hospital Bulk Upload | Paribus Challenge</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fb;color:#172033;font:15px system-ui,Arial}
main{max-width:760px;margin:55px auto;padding:0 18px}.card{background:white;padding:30px;border-radius:16px;box-shadow:0 8px 30px #17203312}
h1{margin:0 0 8px;font-size:27px}.muted{color:#687386;line-height:1.6}
.drop{display:block;border:2px dashed #aab5c5;border-radius:12px;padding:28px;text-align:center;margin:24px 0;background:#fafbfe}
input{max-width:100%;margin-top:14px}button{background:#2457d6;color:white;border:0;padding:12px 20px;border-radius:8px;font-weight:600;cursor:pointer}
button:disabled{opacity:.5;cursor:wait}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#101827;color:#dce7ff;padding:18px;border-radius:10px;margin-top:20px;max-height:460px;overflow:auto}
.note{font-size:13px;color:#687386;margin-top:14px}
</style></head>
<body><main><section class="card">
<h1>Hospital Bulk Processing</h1>
<p class="muted">Upload a CSV file to create up to 20 hospital records. The batch is activated only when every hospital is created successfully.</p>
<form id="uploadForm">
<label class="drop">Choose your CSV file<br><input id="csvFile" type="file" accept=".csv,text/csv" required></label>
<button id="submitBtn" type="submit">Upload and process</button>
</form>
<p class="note">Required columns: name,address · Optional column: phone · Maximum: 20 hospitals</p>
<div id="message" class="muted" role="status"></div><pre id="result" hidden></pre>
</section></main>
<script>
const form=document.getElementById('uploadForm'), btn=document.getElementById('submitBtn');
form.addEventListener('submit',async e=>{
 e.preventDefault(); const file=document.getElementById('csvFile').files[0];
 if(!file)return; const data=new FormData(); data.append('file',file);
 btn.disabled=true; document.getElementById('message').textContent='Processing hospitals…';
 const output=document.getElementById('result'); output.hidden=true;
 try{
  const res=await fetch('/hospitals/bulk',{method:'POST',body:data});
  const body=await res.json(); output.textContent=JSON.stringify(body,null,2); output.hidden=false;
  document.getElementById('message').textContent=res.ok?'Processing finished.':'Request failed.';
 }catch(err){document.getElementById('message').textContent='Could not reach the server: '+err.message;}
 finally{btn.disabled=false;}
});
</script></body></html>
""")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/hospitals/validate")
async def validate_csv(file: UploadFile = File(...)):
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 1 MB upload limit.")
    rows = parse_csv(content)
    return {
        "valid": True,
        "total_hospitals": len(rows),
        "columns": ["name", "address", "phone"],
    }


@app.post("/hospitals/bulk")
async def bulk_create_hospitals(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 1 MB upload limit.")
    rows = parse_csv(content)
    return await process_batch(rows)


@app.get("/hospitals/bulk/{batch_id}")
async def get_batch_status(batch_id: str):
    result = batch_results.get(batch_id)
    if not result:
        raise HTTPException(404, "Batch not found in this application instance.")
    return result
