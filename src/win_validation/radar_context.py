"""Cloudflare Radar outage annotations and traffic anomalies as context."""
from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

from .http import request

API = "https://api.cloudflare.com/client/v4/radar"


def _timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def _fetch(path: str, key: str, params: dict[str, Any], token: str) -> dict[str, Any]:
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    record, body = request(f"cloudflare_radar_{key}", url, "radar_context", token, timeout=20)
    result: dict[str, Any] = {
        "http_status": record.get("http_status"), "evidence_id": record.get("evidence_id"),
        "artifact_path": record.get("artifact_path"), "url": url, "items": [],
        "status": record.get("result_status"),
    }
    if record.get("result_status") != "SUCCESS_WITH_EVIDENCE":
        return result
    try:
        data = json.loads(body)
        items = data["result"][key]
        if data.get("success") is not True or not isinstance(items, list):
            raise ValueError("invalid Radar response")
        result["items"] = [x for x in items if isinstance(x, dict)]
        result["status"] = "OK"
    except (ValueError, TypeError, KeyError):
        result["status"] = "INVALID_RESPONSE"
    return result


def collect_radar_context(asn: str, geo_id: str, token: str, now: datetime) -> dict[str, Any]:
    common = {"location": "PE", "dateRange": "1d", "limit": 100, "format": "JSON"}
    anomalies = _fetch("traffic_anomalies", "trafficAnomalies", common, token)
    annotations = _fetch("annotations", "annotations", {**common, "eventType": "OUTAGE"}, token)
    for item in anomalies["items"]:
        asn_details = item.get("asnDetails") or {}
        item["requested_asn_match"] = str(asn_details.get("asn", "")) == asn if isinstance(asn_details, dict) else False
        item["department_attribution"] = "NOT_ESTABLISHED"
        start = _timestamp(item.get("startDate"))
        item["start_age_minutes"] = round((now - start).total_seconds() / 60, 1) if start else None
    for item in annotations["items"]:
        item["requested_asn_match"] = asn in {str(x) for x in (item.get("asns") or [])}
        item["requested_geoid_match"] = geo_id in {str(x) for x in (item.get("geoIds") or [])}
        start = _timestamp(item.get("startDate"))
        end = _timestamp(item.get("endDate"))
        item["start_age_minutes"] = round((now - start).total_seconds() / 60, 1) if start else None
        item["event_time_status"] = (
            "FUTURE" if start and start > now + timedelta(minutes=2) else
            "ENDED" if end and end < now else
            "STARTED" if start and start <= now else "UNKNOWN"
        )
    return {
        "status": "OK" if anomalies["status"] == annotations["status"] == "OK" else "PARTIAL",
        "as_of_utc": now.isoformat(), "requested_asn": asn, "requested_geoid": geo_id,
        "traffic_anomalies": anomalies, "outage_annotations": annotations,
        "note": "Review-only. Missing ASN or geography is not inferred; NetFlows and Radar are the same Cloudflare family.",
    }
