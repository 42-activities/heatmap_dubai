import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import settings
from .db import engine

log = logging.getLogger("api")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = engine()
    return _engine


def db_ok() -> bool:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def wait_for_db(attempts: int = 5, delay: float = 1.0) -> bool:
    """Try the DB a few times with growing backoff; never raises."""
    for i in range(attempts):
        if db_ok():
            return True
        log.warning("db not ready (attempt %d/%d)", i + 1, attempts)
        if i < attempts - 1:
            time.sleep(delay * (i + 1))
    return False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    wait_for_db()
    yield


app = FastAPI(title="Dubai Bus API", lifespan=lifespan)

_origins = settings.cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "db": db_ok()}
