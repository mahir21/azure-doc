import re
from typing import List, Dict, Any
from dateparser.search import search_dates
from datetime import datetime


def classify_event(text: str) -> str:
    s = text.lower()

    if "hearing" in s:
        return "Hearing"
    if "summons" in s:
        return "Summons/Appearance"
    if "appointment" in s:
        return "Appointment"
    if "deadline" in s:
        return "Deadline"
    return "Unknown"


def normalize_time(dt: datetime) -> str:
    if dt.hour == 0 and dt.minute == 0:
        return ""
    return dt.strftime("%I:%M %p").lstrip("0")


def extract_candidates_from_text(text: str, filename: str) -> List[Dict[str, Any]]:
    results = []
    seen = set()

    found = search_dates(text) or []

    for match, dt in found:
        if not dt:
            continue

        idx = text.lower().find(match.lower())
        snippet = text[max(0, idx - 80): idx + 80]

        event_type = classify_event(snippet)

        key = (dt.isoformat(), event_type, snippet[:40])
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "filename": filename,
            "event_type": event_type,
            "event_date": dt.strftime("%Y-%m-%d"),
            "event_time": normalize_time(dt),
            "snippet": snippet,
        })

    return results