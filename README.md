# Paribus Python Challenge — Hospital Bulk Processing System

A FastAPI application that accepts a CSV upload, creates hospital records through the supplied Hospital Directory API, and activates the batch only after all records are created successfully.

## Features

- `POST /hospitals/bulk` — upload and process a CSV (maximum 20 hospitals).
- `POST /hospitals/validate` — validate CSV structure without creating records.
- `GET /hospitals/bulk/{batch_id}` — retrieve the last result stored for a batch.
- `GET /health` — deployment health check.
- Browser-based upload page at `/`.
- Concurrent outbound requests with a configurable concurrency limit.
- UUID batch IDs, request timeouts, per-row failure reporting, and conditional activation.
- Pytest tests and Docker support.

## CSV format

The header must contain `name,address`. `phone` is optional.

```csv
name,address,phone
General Hospital,123 Main Street,555-0101
City Care Hospital,45 Park Avenue,555-0102
Sunrise Medical Center,78 Lake Road,
```

Maximum 20 non-empty hospital rows. Upload size is limited to 1 MB.

## Run locally

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- Web interface: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Test

```bash
pytest -q
```

## API examples

Validate a CSV:

```bash
curl -X POST http://127.0.0.1:8000/hospitals/validate \
  -F "file=@sample_hospitals.csv"
```

Bulk create:

```bash
curl -X POST http://127.0.0.1:8000/hospitals/bulk \
  -F "file=@sample_hospitals.csv"
```

Fetch a batch result:

```bash
curl http://127.0.0.1:8000/hospitals/bulk/<batch_id>
```

## Deployment on Render (free web service)

1. Push this project to a GitHub repository.
2. Sign in at https://render.com and choose **New → Web Service**.
3. Connect the repository.
4. Select **Free** as the instance type.
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. Add environment variable:
   - `HOSPITAL_DIRECTORY_API_URL` = `https://hospital-directory.onrender.com`
8. Deploy. Your public app URL will look like `https://your-service-name.onrender.com`.

The included `render.yaml` can also be used for Blueprint deployment.

**Free-tier note:** Render free web services sleep after 15 minutes without inbound traffic and can take around a minute to wake. In-memory batch history is lost when the process restarts, and free instances are not intended for production. The first request to the supplied Hospital Directory API may also be slow if that service is sleeping.

## Docker

```bash
docker build -t paribus-hospital-bulk .
docker run -p 8000:8000 paribus-hospital-bulk
```

## Design notes and assumptions

- The supplied API model names the batch field `creation_batch_id`; this implementation sends that field when creating each hospital.
- A batch is activated only if every hospital creation succeeds.
- If a create request fails, successful records remain inactive in the external API. The app reports the failed rows and does not activate the batch. A production-grade extension could add an explicit retry/compensation workflow.
- If activation itself fails, the response reports `activation_failed`; created records may remain inactive.
- The assignment permits in-memory persistence. The result lookup therefore works only while the same application process retains the result.
- The external API's OpenAPI schema should be checked before final submission to confirm its exact request/response fields and status codes.

## Suggested improvements

For a production implementation: persist batch state in PostgreSQL/Redis, move processing to a durable task queue, add idempotency keys and retry/backoff policies, expose true live progress, add authentication/rate limiting, and implement cleanup or compensation for partially created batches.
