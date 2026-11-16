"""IODA geoASN evidence with explicit geographic and freshness checks."""
from __future__ import annotations

import json
import time
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from .http import request

API = "https://api.ioda.inetintel.cc.gatech.edu/v2"


def _normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in value if not unicodedata.combining(c) and c.isalnum())


def _fetch(path: str, params: dict[str, Any], source: str) -> dict[str, Any]:
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    record, body = request(source, url, "ioda_geoasn", timeout=15)
    out = {"status": record.get("result_status"), "http_status": record.get("http_status"),
           "artifact_path": record.get("artifact_path"), "evidence_id": record.get("evidence_id"), "url": url, "data": None}
    if record.get("result_status") != "SUCCESS_WITH_EVIDENCE":
        return out
    try:
        payload = json.loads(body)
        if payload.get("error") not in (None, "") or "data" not in payload:
            raise ValueError("invalid IODA envelope")
        out.update(status="OK", data=payload["data"], copyright=payload.get("copyright"))
    except (ValueError, TypeError, AttributeError):
        out["status"] = "INVALID_RESPONSE"
    return out


def _series_summary(data: Any, source: str, geoasn: str, now: datetime) -> list[dict[str, Any]]:
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], list):
        raise ValueError("invalid IODA series envelope")
    result = []
    for row in data[0]:
        if not isinstance(row, dict) or row.get("entityType") != "geoasn" or str(row.get("entityCode")) != geoasn or row.get("datasource") != source:
            raise ValueError("IODA returned another entity or source")
        values, start, step = row.get("values"), row.get("from"), row.get("step")
        if not isinstance(values, list) or not isinstance(start, (int, float)) or not isinstance(step, (int, float)) or step <= 0:
            raise ValueError("invalid IODA series")
        if not isinstance(row.get("until"), (int, float)) or row["until"] - start != len(values) * step:
            raise ValueError("inconsistent IODA bucket bounds")
        complete = [(start + (i + 1) * step, value) for i, value in enumerate(values)
                    if start + (i + 1) * step <= now.timestamp() and isinstance(value, (int, float)) and not isinstance(value, bool)]
        latest = complete[-1] if complete else None
        age = (now.timestamp() - latest[0]) if latest else None
        result.append({"source": source, "step_seconds": step, "native_step_seconds": row.get("nativeStep"),
                       "latest_value": latest[1] if latest else None,
                       "latest_bucket_end_utc": datetime.fromtimestamp(latest[0], timezone.utc).isoformat() if latest else None,
                       "age_seconds": round(age) if age is not None else None,
                       "coverage": "no_data" if age is None else ("unknown" if step != row.get("nativeStep") else ("recent" if age <= 1800 else "stale")),
                       "null_samples": sum(v is None for v in values)})
    return result


def collect_geoasn(asn: str, department: dict[str, str], now: datetime, window_minutes: int = 180) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "UNKNOWN", "asn": asn, "department": department, "region_candidates": [], "sources": [], "events": None, "alerts": None}
    regions = _fetch("entities/query", {"entityType": "region", "relatedTo": "country/PE", "limit": 100, "page": 0}, "ioda_regions_pe")
    result["region_query"] = {k: v for k, v in regions.items() if k != "data"}
    if regions["status"] != "OK" or not isinstance(regions["data"], list):
        result["status"] = "REGION_QUERY_FAILED"
        return result
    matches = [x for x in regions["data"] if isinstance(x, dict) and x.get("type") == "region"
               and isinstance(x.get("attrs"), dict) and x["attrs"].get("country_code") == "PE"
               and _normalise(str(x.get("name", ""))) == _normalise(department["name"])]
    result["region_candidates"] = [{"code": x.get("code"), "name": x.get("name")} for x in matches]
    if len(matches) != 1 or len(regions["data"]) >= 100:
        result["status"] = "REGION_AMBIGUOUS" if len(matches) > 1 else "REGION_NOT_RESOLVED"
        return result
    geoasn = f"{asn}-{matches[0]['code']}"
    result["geoasn"] = geoasn
    time.sleep(2)
    entity = _fetch("entities/query", {"entityType": "geoasn", "entityCode": geoasn, "limit": 10, "page": 0}, "ioda_geoasn_entity")
    result["entity_query"] = {k: v for k, v in entity.items() if k != "data"}
    valid = [x for x in (entity["data"] if isinstance(entity["data"], list) else []) if isinstance(x, dict)
             and x.get("type") == "geoasn" and str(x.get("code")) == geoasn
             and isinstance(x.get("subnames"), dict) and str(x["subnames"].get("asn", "")).upper() == f"AS{asn}"
             and _normalise(str(x["subnames"].get("region", ""))) == _normalise(department["name"])]
    if entity["status"] != "OK" or len(valid) != 1:
        result["status"] = "GEOASN_NOT_VERIFIED"
        return result
    result["entity"] = valid[0]
    window = {"from": int(now.timestamp()) - window_minutes * 60, "until": int(now.timestamp())}
    for kind in ("events", "alerts"):
        time.sleep(2)
        data = _fetch(f"outages/{kind}", {**window, "entityType": "geoasn", "entityCode": geoasn, "limit": 100, "page": 0}, f"ioda_geoasn_{kind}")
        if data["status"] == "OK":
            if not isinstance(data["data"], list) or any(not isinstance(x, dict) for x in data["data"]):
                data["status"] = "INVALID_RESPONSE"
            else:
                data["count"] = len(data["data"])
                data["more_possible"] = len(data["data"]) >= 100
        result[kind] = data
    for source in ("bgp", "ping-slash24", "merit-nt"):
        time.sleep(2)
        data = _fetch(f"signals/raw/geoasn/{geoasn}", {**window, "datasource": source, "maxPoints": 2000}, "ioda_geoasn_" + source.replace("-", "_"))
        if data["status"] == "OK":
            try:
                data["series"] = _series_summary(data["data"], source, geoasn, now)
            except (ValueError, TypeError, OverflowError):
                data["status"] = "INVALID_RESPONSE"
        data.pop("data", None)
        result["sources"].append(data)
    result["status"] = "OK" if all(x["status"] == "OK" for x in result["sources"]) and all(result[k]["status"] == "OK" for k in ("events", "alerts")) else "PARTIAL"
    result["note"] = "Research context only; absent detections do not establish health, and geoASN mapping does not prove district coverage."
    return result
