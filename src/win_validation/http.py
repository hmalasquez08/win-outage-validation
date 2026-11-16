from __future__ import annotations

import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import certifi

ROOT = Path.cwd()
EV = ROOT / "evidencias"
MANIFEST = EV / "manifest.jsonl"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env() -> dict[str, str]:
    out = os.environ.copy()
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                out.setdefault(key.strip(), value.strip().strip("\"'"))
    return out


def request(
    source: str,
    url: str,
    kind: str,
    token: str | None = None,
    auth_scheme: str = "Bearer",
    method: str = "GET",
    payload: object | None = None,
    sanitizer=None,
    max_response_bytes: int = 10_000_000,
    user_agent: str | None = None,
    timeout: int = 20,
):
    started = time.monotonic()
    at = utc()
    status = None
    error = None
    headers: dict[str, str] = {}
    body = b""
    try:
        req_headers = {
            "User-Agent": user_agent or "win-outage-validation/0.1 (production runner)",
            "Accept": "application/json, application/geo+json, application/xml, text/xml, application/rss+xml, application/atom+xml, text/csv, */*",
        }
        if token:
            req_headers["Authorization"] = f"{auth_scheme} {token}"
        data = json.dumps(payload).encode() if payload is not None else None
        if data is not None:
            req_headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        with urllib.request.urlopen(
            req, timeout=timeout, context=ssl.create_default_context(cafile=certifi.where())
        ) as response:
            status = response.status
            headers = dict(response.headers)
            body = response.read(max_response_bytes)
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = dict(exc.headers)
        body = exc.read(10_000_000)
        error = f"HTTPError: {exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001 - evidence must record every failure
        error = f"{type(exc).__name__}: {exc}"
        body = json.dumps({"error": error, "url": url, "observed_at_utc": at}).encode()

    latency = round(time.monotonic() - started, 3)
    ok = status is not None and 200 <= status < 300
    truncated = bool(
        headers.get("Content-Length", "").isdigit()
        and int(headers["Content-Length"]) > len(body)
    )
    sub = "errors" if not ok else "api_responses/" + source
    path = EV / sub
    path.mkdir(parents=True, exist_ok=True)
    content_type = headers.get("Content-Type", "").lower()
    ext = (
        ".json"
        if "json" in content_type or body[:1] in (b"{", b"[")
        else (
            ".xml"
            if ("xml" in content_type or body.lstrip().startswith(b"<?xml"))
            else (".csv" if "csv" in content_type else ".bin")
        )
    )
    stored = sanitizer(body) if sanitizer and ok else body
    artifact = path / (at.replace(":", "").replace("-", "") + ext)
    artifact.write_bytes(stored)
    digest = hashlib.sha256(stored).hexdigest()
    evidence_id = source + "-" + digest[:12]
    attempt = (
        "TRUNCATED_RESPONSE"
        if truncated
        else (
            "AUTH_BLOCKED"
            if status in (401, 403)
            else (
                "RATE_LIMITED"
                if status == 429
                else (
                    "TRANSIENT_ERROR"
                    if status is None or status >= 500
                    else (
                        "VALIDATION_ERROR"
                        if status >= 400
                        else ("SUCCESS_WITH_EVIDENCE" if ok else "UNAVAILABLE")
                    )
                )
            )
        )
    )
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    signature_input = json.dumps(
        {
            "method": method,
            "endpoint": urllib.parse.urlparse(url)._replace(query="", fragment="").geturl(),
            "query": query,
            "payload": payload,
        },
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    query_signature = hashlib.sha256(signature_input.encode()).hexdigest()
    record = {
        "evidence_id": evidence_id,
        "source_id": source,
        "kind": kind,
        "country": "PE",
        "observed_at_utc": at,
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "result_status": attempt,
        "attempt_status": attempt,
        "query_signature": query_signature,
        "window_start": (query.get("from") or query.get("starttime") or [None])[0],
        "window_end": (query.get("until") or query.get("endtime") or [None])[0],
        "related_report": None,
        "url": url,
        "http_status": status,
        "latency_seconds": latency,
        "error": error,
        "response_bytes": len(stored),
        "original_response_bytes": len(body),
        "truncated": truncated,
        "redaction_applied": bool(sanitizer),
        "headers": {
            key: value
            for key, value in headers.items()
            if key.lower()
            in (
                "content-type",
                "etag",
                "last-modified",
                "retry-after",
                "content-length",
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
                "x-ratelimit-reset",
            )
        },
    }
    with MANIFEST.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record, body
