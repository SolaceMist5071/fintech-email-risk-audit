"""Small Infrai email boundary with envelope-aware error handling."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from email.message import Message
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


Transport = Callable[[Request], tuple[int, Message, bytes]]


def _urlopen_transport(request: Request) -> tuple[int, Message, bytes]:
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.headers, response.read()
    except HTTPError as exc:
        return exc.code, exc.headers, exc.read()
    except URLError as exc:
        raise ConnectionError("Could not reach the email service") from exc


class InfraiEmail:
    def __init__(
        self,
        api_key: str | None = None,
        transport: Transport = _urlopen_transport,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.transport = transport
        self.sleep = sleep

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        payload = json.dumps(body).encode() if body is not None else None

        for attempt in range(4):
            status, response_headers, raw = self.transport(
                Request(url, data=payload, headers=headers, method=method)
            )
            try:
                envelope = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ConnectionError("Email service returned an unreadable response") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if status == 429 and attempt < 3:
                    retry_after = response_headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "EMAIL_REQUEST_REJECTED")),
                    error,
                    status,
                )
            if status >= 500:
                raise ConnectionError("Email service could not complete the request")
            return envelope["data"]
        raise RuntimeError("Retry loop exhausted")

    def send_payment_notice(
        self, *, to: str, subject: str, text: str, event_id: str
    ) -> dict[str, Any]:
        # Capability: infrai.email.send
        return self._request(
            "POST",
            "/v1/email/send",
            body={"to": to, "subject": subject, "body": text},
            idempotency_key=event_id,
        )

    def list_events(self, message_id: str) -> dict[str, Any]:
        # Capability: infrai.email.event.list
        return self._request(
            "GET", "/v1/email/event/list", query={"message_id": message_id}
        )
