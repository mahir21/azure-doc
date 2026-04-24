import os
import re
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any

import httpx
import dateparser
from dateparser.search import search_dates
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from ics import Calendar, Event

app = FastAPI()

AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT", "").rstrip("/")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY", "")
AZURE_API_VERSION = "2024-11-30"
AZURE_MODEL = "prebuilt-layout"


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Date Extractor MVP</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f7fb; color: #111; }
    .wrap { max-width: 1100px; margin: 0 auto; }
    .card { background: white; padding: 20px; border-radius: 14px; box-shadow: 0 2px 10px rgba(0,0,0,.06); margin-bottom: 20px; }
    h1 { margin-top: 0; }
    button { background: #111; color: white; border: 0; padding: 10px 14px; border-radius: 10px; cursor: pointer; }
    button:disabled { opacity: .5; cursor: not-allowed; }
    input[type=file] { margin: 12px 0; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; background: white; }
    th, td { border-bottom: 1px solid #eee; text-align: left; padding: 10px; vertical-align: top; }
    th { background: #fafafa; position: sticky; top: 0; }
    .tag { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #eef2ff; font-size: 12px; }
    .muted { color: #666; font-size: 13px; }
    .status { margin-top: 10px; white-space: pre-wrap; }
    .row-actions { display: flex; gap: 8px; align-items: center; }
    .small { font-size: 12px; color: #666; }
    .controls { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .snippet { max-width: 360px; white-space: normal; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Bulk Date Extractor MVP</h1>
      <div class="muted">Upload scanned PDFs or images. The app uses Azure OCR, finds likely dates, labels them, and exports selected items to a calendar file.</div>
      <input id="files" type="file" multiple />
      <div class="controls">
        <button onclick="extract()">Extract Dates</button>
        <button onclick="selectAll()">Select All</button>
        <button onclick="clearAll()">Clear All</button>
        <button onclick="downloadICS()">Download .ics</button>
      </div>
      <div id="status" class="status muted"></div>
    </div>

    <div class="card">
      <table id="resultsTable">
        <thead>
          <tr>
            <th>Select</th>
            <th>File</th>
            <th>Type</th>
            <th>Date</th>
            <th>Time</th>
            <th>Confidence</th>
            <th>Snippet</th>
          </tr>
        </thead>
        <tbody id="resultsBody">
          <tr><td colspan="7" class="muted">No results yet.</td></tr>
        </tbody>
      </table>
    </div>
  </div>

<script>
let results = [];

function renderTable() {
  const body = document.getElementById("resultsBody");
  body.innerHTML = "";

  if (!results.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">No results yet.</td></tr>';
    return;
  }

  results.forEach((row, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" data-index="${i}" ${row.selected ? "checked" : ""} onchange="toggleRow(${i}, this.checked)"></td>
      <td>${escapeHtml(row.filename)}</td>
      <td><span class="tag">${escapeHtml(row.event_type)}</span></td>
      <td><input value="${escapeHtml(row.event_date || "")}" onchange="updateField(${i}, 'event_date', this.value)" /></td>
      <td><input value="${escapeHtml(row.event_time || "")}" onchange="updateField(${i}, 'event_time', this.value)" /></td>
      <td>${escapeHtml(row.confidence)}</td>
      <td class="snippet">${escapeHtml(row.snippet || "")}</td>
    `;
    body.appendChild(tr);
  });
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function toggleRow(i, checked) {
  results[i].selected = checked;
}

function updateField(i, field, value) {
  results[i][field] = value;
}

function selectAll() {
  results = results.map(r => ({...r, selected: true}));
  renderTable();
}

function clearAll() {
  results = results.map(r => ({...r, selected: false}));
  renderTable();
}

async function extract() {
  const status = document.getElementById("status");
  const fileInput = document.getElementById("files");

  if (!fileInput.files.length) {
    status.textContent = "Choose at least one file.";
    return;
  }

  const fd = new FormData();
  for (const f of fileInput.files) {
    fd.append("files", f);
  }

  status.textContent = "Processing files... this can take a little bit for scanned PDFs.";

  try {
    const res = await fetch("/extract", {
      method: "POST",
      body: fd
    });

    const data = await res.json();

    if (!res.ok) {
      status.textContent = data.detail || "Extraction failed.";
      return;
    }

    results = data.results.map(r => ({...r, selected: true}));
    renderTable();
    status.textContent = `Done. Found ${results.length} candidate event(s).`;
  } catch (err) {
    status.textContent = "Request failed: " + err;
  }
}

async function downloadICS() {
  const selected = results.filter(r => r.selected);

  if (!selected.length) {
    document.getElementById("status").textContent = "Select at least one row first.";
    return;
  }

  const res = await fetch("/download-ics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(selected)
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    document.getElementById("status").textContent = data.detail || "ICS export failed.";
    return;
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "calendar_events.ics";
  a.click();
  window.URL.revokeObjectURL(url);
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HTML)


def classify_event(snippet: str) -> str:
    s = (snippet or "").lower()

    if any(word in s for word in ["hearing", "conference", "calendar call"]):
        return "Hearing"
    if any(word in s for word in ["summons", "summoned", "appear before", "you are hereby summoned", "must appear"]):
        return "Summons/Appearance"
    if "appointment" in s:
        return "Appointment"
    if any(word in s for word in ["deadline", "due", "respond within", "response due", "must file by"]):
        return "Deadline"
    return "Unknown"


def confidence_for(snippet: str, event_type: str, parsed_dt: datetime) -> str:
    score = 0
    s = (snippet or "").lower()

    if event_type != "Unknown":
        score += 2
    if parsed_dt.hour != 0 or parsed_dt.minute != 0:
        score += 1
    if any(k in s for k in ["court", "judge", "hearing", "summons", "appointment", "deadline"]):
        score += 1

    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def normalize_time(dt: datetime) -> str:
    if dt.hour == 0 and dt.minute == 0:
        return ""
    return dt.strftime("%I:%M %p").lstrip("0")


def extract_candidates_from_text(text: str, filename: str) -> List[Dict[str, Any]]:
    results = []
    seen = set()

    found = search_dates(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    ) or []

    for match_text, parsed_dt in found:
        if not parsed_dt:
            continue

        if parsed_dt.year < 2020 or parsed_dt.year > 2035:
            continue

        idx = text.lower().find(match_text.lower())
        if idx == -1:
            idx = 0

        start = max(0, idx - 80)
        end = min(len(text), idx + len(match_text) + 80)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()

        event_type = classify_event(snippet)
        confidence = confidence_for(snippet, event_type, parsed_dt)

        key = (filename, parsed_dt.isoformat(), event_type, snippet[:50])
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "filename": filename,
            "event_type": event_type,
            "event_date": parsed_dt.strftime("%Y-%m-%d"),
            "event_time": normalize_time(parsed_dt),
            "confidence": confidence,
            "snippet": snippet,
        })

    return results


async def azure_ocr_bytes(file_bytes: bytes, filename: str) -> str:
    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise HTTPException(
            status_code=500,
            detail="Set AZURE_DI_ENDPOINT and AZURE_DI_KEY first."
        )

    post_url = (
        f"{AZURE_DI_ENDPOINT}/documentintelligence/documentModels/"
        f"{AZURE_MODEL}:analyze?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_DI_KEY,
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        post_resp = await client.post(post_url, headers=headers, content=file_bytes)

        if post_resp.status_code not in (200, 202):
            raise HTTPException(
                status_code=500,
                detail=f"Azure analyze start failed for {filename}: {post_resp.text}"
            )

        operation_location = post_resp.headers.get("operation-location")
        if not operation_location:
            # Some responses may come back inline, but for this API we expect polling.
            data = post_resp.json()
            return data.get("analyzeResult", {}).get("content", "")

        for _ in range(60):
            poll_resp = await client.get(
                operation_location,
                headers={"Ocp-Apim-Subscription-Key": AZURE_DI_KEY}
            )

            if poll_resp.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Azure polling failed for {filename}: {poll_resp.text}"
                )

            data = poll_resp.json()
            status = data.get("status")

            if status == "succeeded":
                return data.get("analyzeResult", {}).get("content", "")
            if status == "failed":
                raise HTTPException(
                    status_code=500,
                    detail=f"Azure OCR failed for {filename}: {json.dumps(data)}"
                )

            await sleep_async(1.5)

    raise HTTPException(status_code=500, detail=f"Azure OCR timed out for {filename}.")


async def sleep_async(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


@app.post("/extract")
async def extract(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    all_results = []

    for file in files:
        content = await file.read()
        text = await azure_ocr_bytes(content, file.filename)
        candidates = extract_candidates_from_text(text, file.filename)
        all_results.extend(candidates)

    return {"results": all_results}


@app.post("/download-ics")
async def download_ics(events: List[Dict[str, Any]]):
    if not events:
        raise HTTPException(status_code=400, detail="No events selected.")

    cal = Calendar()

    for row in events:
        event_date = (row.get("event_date") or "").strip()
        event_time = (row.get("event_time") or "").strip()
        event_type = (row.get("event_type") or "Event").strip()
        filename = (row.get("filename") or "Document").strip()
        snippet = (row.get("snippet") or "").strip()

        if not event_date:
            continue

        dt_text = event_date if not event_time else f"{event_date} {event_time}"
        parsed = dateparser.parse(dt_text)

        if not parsed:
            continue

        e = Event()
        e.name = f"{event_type} — {filename}"
        e.begin = parsed
        e.description = snippet
        cal.events.add(e)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ics") as tmp:
        tmp.write(str(cal).encode("utf-8"))
        tmp_path = tmp.name

    return FileResponse(tmp_path, filename="calendar_events.ics", media_type="text/calendar")