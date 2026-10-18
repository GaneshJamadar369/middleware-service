
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

EMAIL = "23f3003450@ds.study.iitm.ac.in"
ALLOWED_ORIGINS = ["https://app-h6sqte.example.com"]
LIMIT = 15
WINDOW = 10

buckets = defaultdict(deque)
lock = Lock()


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.monotonic()

        with lock:
            bucket = buckets[client_id]
            while bucket and now - bucket[0] >= WINDOW:
                bucket.popleft()

            if len(bucket) >= LIMIT:
                retry_after = max(1, int(WINDOW - (now - bucket[0]) + 0.999))
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
                response.headers["X-Request-ID"] = request_id
                return response

            bucket.append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
)


@app.get("/ping")
def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
