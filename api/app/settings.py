import os


def database_url() -> str | None:
    return os.environ.get("DATABASE_URL")


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*")
    return [o.strip() for o in raw.split(",") if o.strip()]


def data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data")
