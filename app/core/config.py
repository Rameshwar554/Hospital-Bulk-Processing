import os

DIRECTORY_API_URL = os.getenv(
    "HOSPITAL_DIRECTORY_API_URL",
    "https://hospital-directory.onrender.com",
).rstrip("/")

MAX_HOSPITALS = 20
MAX_FILE_BYTES = 1024 * 1024
MAX_CONCURRENT_REQUESTS = max(1, int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")))
REQUEST_TIMEOUT_SECONDS = 30.0
CONNECT_TIMEOUT_SECONDS = 10.0
