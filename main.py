
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "23f3003450@ds.study.iitm.ac.in"

# Include the exam page's actual origin if it differs.
ALLOWED_ORIGINS = [
    "https://app-h6sqte.example.com",
    "https://exam.sanand.workers.dev",
]

RATE_LIMIT = 15
WINDOW_SECONDS = 10

app = FastAPI()

rate_buckets = defaultdict(deque)
rate_lock = Lock()




@app.middleware("http")
async def request_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.monotonic()

        with rate_lock:
            bucket = rate_buckets[client_id]

            while bucket and now - bucket[0] >= WINDOW_SECONDS:
                bucket.popleft()

            if len(bucket) >= RATE_LIMIT:
                retry_after = max(
                    1,
                    int(WINDOW_SECONDS - (now - bucket[0]) + 0.999),
                )
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={
                        "Retry-After": str(retry_after),
                        "X-Request-ID": request_id,
                    },
                )
                return response

            bucket.append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/ping")
def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.get("/ping")
def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.headers.get("X-Request-ID")
        or getattr(request.state, "request_id", None),
    }


# Register CORS last so it handles preflight before the rate limiter.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-h6sqte.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
    allow_credentials=False,
)
