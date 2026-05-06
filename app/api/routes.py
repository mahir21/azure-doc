from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List
import tempfile
from pathlib import Path
from ics import Calendar, Event
import dateparser
from azure.core.exceptions import AzureError

from app.services.ocr_service import azure_ocr_bytes
from app.services.extraction_service import extract_candidates_from_text
from app.services.blob_service import upload_file

router = APIRouter()

FRONTEND_PATH = Path(__file__).resolve().parents[2] / "index.html"


@router.get("/")
async def home():
    return FileResponse(FRONTEND_PATH)


@router.post("/extract")
async def extract(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        content = await file.read()

        # upload to blob
        try:
            upload_file(file.filename, content)
        except AzureError as exc:
            raise HTTPException(500, f"Blob upload failed: {exc}") from exc

        # OCR
        text = await azure_ocr_bytes(content, file.filename)

        # extract events
        extracted = extract_candidates_from_text(text, file.filename)
        results.extend(extracted)

    return {"results": results}


@router.post("/download-ics")
async def download_ics(events: list[dict]):
    cal = Calendar()

    for e in events:
        dt = dateparser.parse(
            f"{e['event_date']} {e.get('event_time') or ''}"
        )

        if not dt:
            continue

        event = Event()
        event.name = f"{e['event_type']} — {e['filename']}"
        event.begin = dt
        event.description = e.get("snippet", "")
        cal.events.add(event)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ics") as f:
        f.write(str(cal).encode())
        path = f.name

    return FileResponse(path, filename="events.ics")
