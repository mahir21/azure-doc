import httpx
from fastapi import HTTPException

from app.core.config import (
    AZURE_DI_ENDPOINT,
    AZURE_DI_KEY,
    AZURE_API_VERSION,
    AZURE_MODEL,
)


async def azure_ocr_bytes(file_bytes: bytes, filename: str) -> str:
    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise HTTPException(500, "Azure OCR not configured")

    url = (
        f"{AZURE_DI_ENDPOINT}/documentintelligence/documentModels/"
        f"{AZURE_MODEL}:analyze?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_DI_KEY,
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=headers, content=file_bytes)

        if r.status_code not in (200, 202):
            raise HTTPException(500, r.text)

        op_url = r.headers.get("operation-location")

        if not op_url:
            return r.json().get("analyzeResult", {}).get("content", "")

        for _ in range(60):
            poll = await client.get(op_url, headers={
                "Ocp-Apim-Subscription-Key": AZURE_DI_KEY
            })

            data = poll.json()

            if data.get("status") == "succeeded":
                return data["analyzeResult"]["content"]

            if data.get("status") == "failed":
                raise HTTPException(500, data)

            import asyncio
            await asyncio.sleep(1.5)

    raise HTTPException(500, "OCR timeout")