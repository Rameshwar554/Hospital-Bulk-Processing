# Hospital Bulk Processing System

A FastAPI service built for the **Paribus Python Challenge**. It accepts a CSV containing hospital details, creates each hospital through the provided Hospital Directory API, and activates the batch only after every hospital has been created successfully.

## Live Application

- **Application:** https://hospital-bulk-processing-fczp.onrender.com
- **Swagger / OpenAPI documentation:** https://hospital-bulk-processing-fczp.onrender.com/docs
- **Health check:** https://hospital-bulk-processing-fczp.onrender.com/health
- **Hospital Directory API (upstream):** https://hospital-directory.onrender.com
- **Upstream API documentation:** https://hospital-directory.onrender.com/docs
- **Source code:** https://github.com/Rameshwar554/Hospital-Bulk-Processing

> The application is hosted on Render's free instance. After a period of inactivity, the service may spin down; the first request after that can take around 50 seconds or more while it starts.

## Assignment Overview

The task is to build a separate bulk-processing service that integrates with the supplied Hospital Directory API.

### Functional requirements

1. Accept a CSV file through a multipart form upload.
2. Validate the CSV structure and hospital records.
3. Generate a unique UUID for each bulk-processing batch.
4. Create each hospital by calling `POST /hospitals/` on the upstream Hospital Directory API, passing the batch ID as `creation_batch_id`.
5. Activate the batch through the upstream `PATCH /hospitals/batch/{batch_id}/activate` endpoint only when all hospital creation requests succeed.
6. Return processing information, including the batch ID, counts, per-hospital outcomes, processing time, and batch activation status.

### Constraints

- Maximum of **20 hospital records per CSV**.
- CSV upload size limit: **1 MB**.
- Required CSV columns: `name`, `address`.
- Optional CSV column: `phone`.
- Python with FastAPI.
- In-memory batch-result storage is acceptable for this assignment.
- Public deployment is required; this application is deployed on Render.

## Application API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Browser-based CSV upload interface |
| `GET` | `/health` | Health check for the running service |
| `POST` | `/hospitals/validate` | Validate an uploaded CSV without creating hospitals |
| `POST` | `/hospitals/bulk` | Upload a CSV and process the hospital batch |
| `GET` | `/hospitals/bulk/{batch_id}` | Retrieve the stored result for a processed batch |

Interactive request/response schemas are available in the [Swagger documentation](https://hospital-bulk-processing-fczp.onrender.com/docs).

### Example CSV

```csv
name,address,phone
General Hospital,123 Main Street,555-0101
City Care Hospital,45 Park Avenue,555-0102
Sunrise Medical Center,78 Lake Road,
```

### Example requests

Validate a CSV:

```bash
curl -X POST "https://hospital-bulk-processing-fczp.onrender.com/hospitals/validate" \
  -H "accept: application/json" \
  -F "file=@sample_hospitals.csv"
```

Process a bulk upload:

```bash
curl -X POST "https://hospital-bulk-processing-fczp.onrender.com/hospitals/bulk" \
  -H "accept: application/json" \
  -F "file=@sample_hospitals.csv"
```

Retrieve a batch result (replace `<batch_id>` with the UUID returned by the bulk endpoint):

```bash
curl -X GET "https://hospital-bulk-processing-fczp.onrender.com/hospitals/bulk/<batch_id>" \
  -H "accept: application/json"
```

## Project Structure

The application code is separated by responsibility to keep routing, request handling, business logic, validation, schemas, configuration, and HTML independent.

```text
Hospital-Bulk-Processing/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application setup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # API route definitions and router registration
│   │   └── handlers.py            # Route/request handlers
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Environment-based configuration and limits
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── hospital.py            # Pydantic hospital data schemas
│   ├── validators/
│   │   ├── __init__.py
│   │   └── csv_validator.py       # CSV parsing and validation
│   ├── services/
│   │   ├── __init__.py
│   │   └── bulk_processor.py      # Upstream API calls and batch processing
│   └── templates/
│       └── index.html             # Browser-based upload page
├── tests/
│   ├── test_csv.py                # CSV validation tests
│   └── test_processing.py         # Bulk-processing tests
├── sample_hospitals.csv           # Sample input file
├── requirements.txt               # Python dependencies
├── pytest.ini                     # Pytest configuration
├── Dockerfile                     # Docker image configuration
├── .dockerignore
├── .gitignore
├── render.yaml                    # Render deployment configuration
└── README.md
```

## Processing Workflow

```text
CSV Upload
    |
    v
Validate file size, headers, and rows
    |
    v
Generate UUID batch ID
    |
    v
Create hospital records through the Hospital Directory API
    |
    +---- Any creation fails? ---- Yes ---> Report failures; do not activate batch
    |
    No
    |
    v
PATCH upstream batch activation endpoint
    |
    v
Return batch summary and per-hospital results
```

## Implementation Details

- **Asynchronous HTTP requests:** Uses `httpx.AsyncClient` for calls to the upstream service.
- **Concurrent processing:** Hospital creation requests are run concurrently with a configurable concurrency limit.
- **Batch identification:** Generates a UUID and sends it as `creation_batch_id` for each hospital.
- **Conditional activation:** The batch is activated only if all hospital creation operations succeed.
- **Validation:** Checks CSV headers and records, enforces the 20-hospital limit, and rejects files larger than 1 MB.
- **Failure reporting:** Captures individual hospital outcomes and reports processing and activation failures.
- **Batch lookup:** Keeps processing results in memory so they can be retrieved by batch ID while the process remains running.
- **Automated tests:** Includes tests for CSV validation and bulk-processing behavior.
- **Container support:** Includes a Dockerfile.
- **Deployment configuration:** Includes `render.yaml` for Render deployment.

## Configuration

The upstream API URL and processing limits are configured in the application. The upstream URL can be supplied through this environment variable:

| Variable | Description | Value used in deployment |
|---|---|---|
| `HOSPITAL_DIRECTORY_API_URL` | Base URL of the Hospital Directory API | `https://hospital-directory.onrender.com` |

The Render service uses Python 3.11.9. Its build and start commands are:

```bash
pip install -r requirements.txt
```

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Run Locally

Python 3.10+ is recommended.

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API
uvicorn app.main:app --reload
```

Open these local URLs:

- Web interface: http://127.0.0.1:8000/
- Swagger documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Run Tests

```bash
pytest -q
```

## Run with Docker

Build the image:

```bash
docker build -t hospital-bulk-processing .
```

Run the container:

```bash
docker run --rm -p 8000:8000 \
  -e HOSPITAL_DIRECTORY_API_URL=https://hospital-directory.onrender.com \
  hospital-bulk-processing
```

Then open http://127.0.0.1:8000/docs.

## Deployment

The service is deployed on [Render](https://render.com) and connected to the GitHub repository.

- **Render service URL:** https://hospital-bulk-processing-fczp.onrender.com
- **Swagger URL:** https://hospital-bulk-processing-fczp.onrender.com/docs
- **Health-check URL:** https://hospital-bulk-processing-fczp.onrender.com/health
- **Deployment configuration:** `render.yaml`
- **Auto-deploy:** Enabled for commits pushed to the connected deployment branch.

To deploy an update, commit and push the changes to the connected GitHub branch. Render will start a new deployment automatically when Auto-Deploy is enabled. Check the service's **Events** page and confirm the latest deployment status is **Live**.

## Limitations and Possible Improvements

- Batch results are held in process memory. They are not durable and may be lost when the service restarts or is redeployed.
- The batch-result endpoint returns the stored result after processing; it is not a durable, real-time progress stream.
- If some hospital creations succeed and another fails, the successful upstream records remain inactive; the batch is not activated. A retry or compensation workflow could be added.
- If the upstream activation request fails, the service reports the activation failure; created records may remain inactive.
- For production use, batch state could be persisted in PostgreSQL or Redis, and processing could be moved to a durable task queue with retry/backoff, idempotency, authentication, rate limiting, and operational monitoring.

## Upstream Hospital Directory API

The bulk service integrates with the following supplied endpoints:

| Method | Upstream endpoint | Purpose |
|---|---|---|
| `POST` | `/hospitals/` | Create an individual hospital |
| `GET` | `/hospitals/` | List hospitals |
| `GET` | `/hospitals/batch/{batch_id}` | Retrieve hospitals belonging to a batch |
| `PATCH` | `/hospitals/batch/{batch_id}/activate` | Activate all hospitals in a batch |
| `DELETE` | `/hospitals/batch/{batch_id}` | Delete hospitals belonging to a batch |

See the upstream [Swagger documentation](https://hospital-directory.onrender.com/docs) for its complete API contract.
