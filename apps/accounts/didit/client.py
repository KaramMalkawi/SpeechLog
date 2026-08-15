from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings


class DiditError(Exception):
    pass


class DiditClient:
    def __init__(self) -> None:
        self.base_url = settings.DIDIT_API_BASE_URL.rstrip("/")
        self.api_key = settings.DIDIT_API_KEY

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def create_session(
        self,
        *,
        workflow_id: str,
        vendor_data: str,
        callback: str,
        callback_method: str = "both",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        payload = {
            "workflow_id": workflow_id,
            "vendor_data": vendor_data,
            "callback": callback,
            # Redirect whichever device finishes verification (mobile browser).
            "callback_method": callback_method,
        }
        if metadata:
            payload["metadata"] = metadata

        response = httpx.post(
            f"{self.base_url}/v3/session/",
            headers=self._headers(),
            json=payload,
            timeout=30.0,
        )
        if response.status_code >= 400:
            raise DiditError(response.text)
        return response.json()

    def get_session_decision(self, session_id: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/v3/session/{session_id}/decision/",
            headers={"x-api-key": self.api_key},
            timeout=30.0,
        )
        if response.status_code >= 400:
            raise DiditError(response.text)
        return response.json()
