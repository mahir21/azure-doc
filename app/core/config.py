import os
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_env_file()

AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT", "").rstrip("/")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY", "")

AZURE_API_VERSION = "2024-11-30"
AZURE_MODEL = "prebuilt-layout"

BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING", "")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER", "pdf-files")
