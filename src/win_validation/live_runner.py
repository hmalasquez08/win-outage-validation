"""Manual live runner for the Win outage trigger.

One invocation queries Cloudflare NetFlows, IODA and optionally current
corroboration sources, evaluates the fail-closed policy and always renders XML.
Events are included only when a qualified decision exists.

This is a manual runner, not a daemon. It never activates campaigns.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .creative_trigger import MAX_SIGNAL_AGE, assess
from .trigger_feed_xml import build_empty_feed, build_feed, validate_feed, write_feed

ROOT = Path.cwd()
REPORTS = ROOT / "reports"
LIVE_OUTPUT = ROOT / "xml" / "trigger_feed_live.xml"
UBIGEO_REPORT = ROOT / "data" / "ubigeo_hibrido.csv"
CLOUDFLARE_API = "https://api.cloudflare.com/client/v4/radar"
IODA_API = "https://api.ioda.inetintel.cc.gatech.edu/v2"
ASNS = {"movistar": "6147", "claro": "12252", "entel": "21575", "bitel": "262210"}
NETFLOWS_RULE = {
    "minimum_paired_intervals": 8,
    "maximum_median_delta": -0.02,
    "minimum_fraction_below_comparator": 0.90,
}
GEOGRAPHY_ALIASES = {"cusco": "cuzco"}


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without timezone: {value}")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch) and ch.isalnum())


def _strip_admin_suffix(value: str) -> str:
    normalised = _normalise(value)
    for suffix in ("department", "departamento", "region", "provincia"):
        if normalised.endswith(suffix) and len(normalised) > len(suffix):
            normalised = normalised[: -len(suffix)]
            break
    return GEOGRAPHY_ALIASES.get(normalised, normalised)


def load_departments(path: Path = UBIGEO_REPORT) -> dict[str, dict[str, str]]:
    """Return departments indexed by UBIGEO prefix and normalised name."""
    if not path.exists():
        raise FileNotFoundError(f"UBIGEO report not found: {path}")
    by_code: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            code = (row.get("UBIGEO") or "").strip()[:2]
            name = (row.get("DEPARTAMENTO") or "").strip()
            if len(code) == 2 and code.isdigit() and name and code not in by_code:
                by_code[code] = {"code": code, "name": name}
    if not by_code:
        raise ValueError(f"No departments found in {path}")
    return by_code


def resolve_department(value: str, path: Path = UBIGEO_REPORT) -> dict[str, str]:
    """Accept a department name, a 2-digit code or a full UBIGEO code."""
    departments = load_departments(path)
    cleaned = value.strip()
    if cleaned.isdigit():
        code = cleaned[:2]
        if code in departments:
            return departments[code]
    target = _strip_admin_suffix(cleaned)
    matches = [item for item in departments.values() if _strip_admin_suffix(item["name"]) == target]
    if len(matches) == 1:
        return matches[0]
    available = ", ".join(sorted(item["name"] for item in departments.values()))
    raise ValueError(f"Unknown department {value!r}. Available: {available}")


def _netflow_url(
    asn: str, geo_id: str, current_start: datetime, current_end: datetime,
    comparison_start: datetime, comparison_end: datetime,
) -> str:
    params = [
        ("name", "current"), ("dateStart", _format_utc(current_start)), ("dateEnd", _format_utc(current_end)),
        ("geoId", geo_id), ("asn", asn), ("product", "ALL"),
        ("name", "comparator"), ("dateStart", _format_utc(comparison_start)), ("dateEnd", _format_utc(comparison_end)),
        ("geoId", geo_id), ("asn", asn), ("product", "ALL"),
        ("aggInterval", "15m"), ("normalization", "MIN0_MAX"), ("format", "JSON"),
    ]
    return f"{CLOUDFLARE_API}/netflows/timeseries?" + urllib.parse.urlencode(params)


def netflow_metrics(current: list[Any], comparator: list[Any]) -> dict[str, Any]:
    """Compare two equal-length-normalised NetFlows series."""
    current_values = [float(value) for value in current if value not in (None, "")]
    comparator_values = [float(value) for value in comparator if value not in (None, "")]
    points = min(len(current_values), len(comparator_values))
    paired = [left - right for left, right in zip(current_values[:points], comparator_values[:points])]
    median_delta = statistics.median(paired) if paired else None
    fraction_below = sum(value < 0 for value in paired) / points if points else None
    candidate = bool(
        points >= NETFLOWS_RULE["minimum_paired_intervals"]
        and median_delta is not None
        and median_delta < NETFLOWS_RULE["maximum_median_delta"]
        and fraction_below is not None
        and fraction_below >= NETFLOWS_RULE["minimum_fraction_below_comparator"]
    )
    return {
        "paired_intervals": points,
        "current_points": len(current_values),
        "comparator_points": len(comparator_values),
        "median_delta": median_delta,
        "fraction_below_comparator": fraction_below,
        "candidate": candidate,
    }


def _parse_netflow_body(body: bytes) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    obj = json.loads(body)
    result = obj.get("result", {}) if isinstance(obj, dict) else {}
    current = result.get("current", {}) if isinstance(result, dict) else {}
    comparator = result.get("comparator", {}) if isinstance(result, dict) else {}
    meta = result.get("meta", {}) if isinstance(result, dict) else {}
    return (
        current if isinstance(current, dict) else {},
        comparator if isinstance(comparator, dict) else {},
        meta if isinstance(meta, dict) else {},
    )


def _aligned_netflows(
    current: dict[str, Any], comparator: dict[str, Any],
    *, current_start: datetime | None = None, comparison_start: datetime | None = None,
) -> tuple[list[float], list[float], str | None, int, int]:
    """Pair current/comparator by relative timestamp, skipping null or malformed points."""
    def by_offset(series: dict[str, Any], window_start: datetime | None) -> dict[int, tuple[datetime, float]]:
        timestamps = series.get("timestamps", [])
        values = series.get("values", [])
        parsed: list[tuple[datetime, float]] = []
        for timestamp, value in zip(timestamps, values):
            if value in (None, ""):
                continue
            try:
                parsed.append((_parse_utc(str(timestamp)), float(value)))
            except (TypeError, ValueError):
                continue
        if not parsed:
            return {}
        parsed.sort(key=lambda item: item[0])
        base = window_start or parsed[0][0]
        return {
            int((observed - base).total_seconds()): (observed, value)
            for observed, value in parsed
        }

    current_map = by_offset(current, current_start)
    comparator_map = by_offset(comparator, comparison_start)
    common = sorted(set(current_map) & set(comparator_map))
    if common:
        observed_at = _format_utc(current_map[common[-1]][0])
    elif current_map:
        observed_at = _format_utc(max(value[0] for value in current_map.values()))
    else:
        observed_at = None
    return (
        [current_map[offset][1] for offset in common],
        [comparator_map[offset][1] for offset in common],
        observed_at,
        len(current_map),
        len(comparator_map),
    )


def fetch_netflows(
    operator: str, asn: str, geo_id: str, window_minutes: int, token: str, now: datetime,
) -> dict[str, Any]:
    from .http import request

    end = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0) - timedelta(minutes=15)
    start = end - timedelta(minutes=window_minutes)
    comparison_start = start - timedelta(days=7)
    comparison_end = end - timedelta(days=7)
    url = _netflow_url(asn, geo_id, start, end, comparison_start, comparison_end)
    record, body = request(f"cloudflare_netflows_live_{operator}", url, "live_signal", token)
    try:
        current_series, comparator_series, meta = _parse_netflow_body(body)
    except (ValueError, TypeError, json.JSONDecodeError):
        current_series, comparator_series, meta = {}, {}, {}
    current, comparator, observed_at, current_points, comparator_points = _aligned_netflows(
        current_series, comparator_series, current_start=start, comparison_start=comparison_start,
    )
    metrics = netflow_metrics(current, comparator)
    metrics["current_points"] = current_points
    metrics["comparator_points"] = comparator_points
    age_minutes = None
    if observed_at:
        try:
            age_minutes = round((now - _parse_utc(observed_at)).total_seconds() / 60, 1)
        except ValueError:
            observed_at = None
    return {
        "operator": operator, "asn": asn, "geo_id": geo_id,
        "http_status": record.get("http_status"), "evidence_id": record.get("evidence_id"),
        "artifact_path": record.get("artifact_path"), "url": url,
        "window_start_utc": _format_utc(start), "window_end_utc": _format_utc(end),
        "comparison_start_utc": _format_utc(comparison_start),
        "comparison_end_utc": _format_utc(comparison_end),
        "observed_at_utc": observed_at, "age_minutes": age_minutes,
        "last_updated_utc": meta.get("lastUpdated"),
        "normalization": meta.get("normalization"), "aggregation_interval": meta.get("aggInterval"),
        **metrics,
    }


def fetch_ioda(operator: str, asn: str, window_minutes: int, now: datetime) -> dict[str, Any]:
    from .http import request

    start = now - timedelta(minutes=window_minutes)
    params = {"entityType": "asn", "entityCode": asn, "from": int(start.timestamp()), "until": int(now.timestamp()), "limit": 100}
    url = f"{IODA_API}/outages/events?" + urllib.parse.urlencode(params)
    record, body = request(f"ioda_live_{operator}", url, "live_signal")
    events: list[dict[str, Any]] = []
    try:
        data = json.loads(body).get("data", [])
        if isinstance(data, list):
            events = [item for item in data if isinstance(item, dict)]
    except (ValueError, TypeError, json.JSONDecodeError):
        pass
    starts = [int(item["start"]) for item in events if isinstance(item.get("start"), (int, float))]
    observed_at = _format_utc(datetime.fromtimestamp(max(starts), timezone.utc)) if starts else None
    return {
        "operator": operator, "asn": asn, "http_status": record.get("http_status"),
        "evidence_id": record.get("evidence_id"), "artifact_path": record.get("artifact_path"),
        "url": url, "window_start_utc": _format_utc(start), "window_end_utc": _format_utc(now),
        "event_count": len(events), "observed_at_utc": observed_at,
        "datasources": sorted({str(item.get("datasource")) for item in events if item.get("datasource")}),
    }


def _news_area_matches(areas: str, department_code: str) -> bool:
    for encoded in areas.split(";"):
        try:
            _level, _name, code = encoded.split(":", 2)
        except ValueError:
            continue
        if code.strip()[:2] == department_code:
            return True
    return False


def collect_news_corroboration(
    operator: str, department_code: str, minimum_outlets: int, now: datetime,
    news_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .news import collect_current_news

    path = REPORTS / "current_news_candidates.csv"
    if news_snapshot is not None:
        summary = news_snapshot["summary"]
        candidates = list(news_snapshot.get("candidates", []))
    else:
        summary = collect_current_news()
        candidates = []
        if path.exists():
            with path.open(newline="", encoding="utf-8-sig") as handle:
                candidates = list(csv.DictReader(handle))
    matched: list[dict[str, str]] = []
    for row in candidates:
        if str(row.get("news_candidate", "")).casefold() != "true":
            continue
        if str(row.get("possibly_socially_derived", "")).casefold() == "true":
            continue
        operators = {item.strip().casefold() for item in str(row.get("operators", "")).split(";") if item.strip()}
        if operator not in operators:
            continue
        if not _news_area_matches(str(row.get("areas", "")), department_code):
            continue
        try:
            published = _parse_utc(str(row.get("published_at_utc", "")))
        except ValueError:
            continue
        age = now - published
        if age > MAX_SIGNAL_AGE or age < -timedelta(minutes=2):
            continue
        matched.append(row)
    outlets = sorted({row.get("outlet", "") for row in matched if row.get("outlet")})
    return {
        "summary": summary, "candidates_report": path.relative_to(ROOT).as_posix() if path.exists() else None,
        "matched": matched, "outlets": outlets, "minimum_outlets": minimum_outlets,
        "eligible": len(outlets) >= minimum_outlets,
    }


def collect_social_support(
    operator: str, department_code: str, now: datetime, *, platforms: list[str] | None = None,
    minimum_items: int = 1, max_posts: int = 3, max_comments: int = 10,
    shared_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .social import collect_social_corroboration

    return collect_social_corroboration(
        operator, department_code, now, platforms=platforms,
        minimum_items=minimum_items, max_posts=max_posts, max_comments=max_comments,
        shared_summary=shared_summary,
    )


def resolve_cloudflare_geography(department: dict[str, str], token: str) -> dict[str, Any]:
    from .http import request

    url = f"{CLOUDFLARE_API}/geolocations?" + urllib.parse.urlencode({"location": "PE", "limit": 100, "format": "JSON"})
    record, body = request("cloudflare_geolocations_live_pe", url, "geography", token)
    geolocations: list[dict[str, Any]] = []
    try:
        result = json.loads(body).get("result", {})
        geolocations = result.get("geolocations", []) if isinstance(result, dict) else []
    except (ValueError, TypeError, json.JSONDecodeError):
        pass
    target = _strip_admin_suffix(department["name"])
    matches = [
        item for item in geolocations
        if isinstance(item, dict) and item.get("type") == "ADM1"
        and _strip_admin_suffix(str(item.get("name", ""))) == target
    ]
    if len(matches) != 1:
        return {
            "status": "NOT_RESOLVED", "department": department, "matches": len(matches),
            "http_status": record.get("http_status"), "evidence_id": record.get("evidence_id"),
            "artifact_path": record.get("artifact_path"), "url": url,
        }
    item = matches[0]
    return {
        "status": "RESOLVED", "department": department, "name": item.get("name"),
        "geo_id": str(item.get("geoId")), "http_status": record.get("http_status"),
        "evidence_id": record.get("evidence_id"), "artifact_path": record.get("artifact_path"), "url": url,
    }


def build_signals(
    operator: str, department: dict[str, str], technology: str,
    netflows: dict[str, Any], ioda: dict[str, Any], news: dict[str, Any] | None,
    social: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    geography = {
        "country": "PE", "level": "department", "code": department["code"],
        "name": department["name"], "verified": True,
        "cloudflare_geo_id": netflows.get("geo_id"),
    }
    signals: list[dict[str, Any]] = []
    if netflows.get("candidate") and netflows.get("observed_at_utc") and netflows.get("evidence_id"):
        signals.append({
            "signal_id": netflows["evidence_id"], "family": "cloudflare_netflows",
            "kind": "internet_degradation", "operator": operator, "technology": technology,
            "observed_at": netflows["observed_at_utc"], "source_status": "ok", "geography": dict(geography),
        })
    if news and news.get("eligible"):
        for row in news.get("matched", []):
            outlet = str(row.get("outlet", "")).strip()
            published = str(row.get("published_at_utc", "")).strip()
            if not outlet or not published:
                continue
            signals.append({
                "signal_id": f"news:{outlet}:{published}", "family": "news_rss",
                "kind": "internet_complaints", "operator": operator, "technology": "internet_unspecified",
                "observed_at": published, "source_status": "ok", "geography": dict(geography),
            })
    if social and social.get("eligible"):
        for row in social.get("matched", []):
            observed = str(row.get("published_at_utc", "")).strip()
            platform = str(row.get("platform", "")).strip()
            item_id = str(row.get("platform_item_id", "")).strip() or str(row.get("url", "")).strip()
            if not observed or not platform or not item_id:
                continue
            signals.append({
                "signal_id": f"social:{platform}:{row.get('item_type', '')}:{item_id}",
                "family": "social_public", "kind": "internet_complaints",
                "operator": operator, "technology": "internet_unspecified",
                "observed_at": observed, "source_status": "ok", "geography": dict(geography),
            })
    if ioda.get("event_count") and ioda.get("observed_at_utc") and ioda.get("evidence_id"):
        signals.append({
            "signal_id": ioda["evidence_id"], "family": "ioda", "kind": "internet_outage",
            "operator": operator, "technology": "internet_unspecified",
            "observed_at": ioda["observed_at_utc"], "source_status": "ok",
            "geography": {**geography, "verified": False, "scope": "asn_only"},
        })
    return signals


def _write_report(result: dict[str, Any]) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / "live_run_latest.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def _empty_output(output: Path | None, system_status: str = "ok") -> tuple[Path, dict[str, Any]]:
    path = output or LIVE_OUTPUT
    write_feed(build_empty_feed(datetime.now(timezone.utc), system_status=system_status), path)
    return path, validate_feed(path)


def _run_once(
    operator: str, department_value: str, *, window_minutes: int = 180, technology: str = "internet_unspecified",
    use_news: bool = False, minimum_news_outlets: int = 2, use_social: bool = False,
    minimum_social_items: int = 1, social_platforms: list[str] | None = None, use_osiptel_news: bool = False,
    confirm: bool = False, creative_url: str | None = None, output: Path | None = None,
    social_summary: dict[str, Any] | None = None, news_snapshot: dict[str, Any] | None = None,
    progress=None, write_feed: bool = True,
) -> dict[str, Any]:
    from .http import load_env

    if operator not in ASNS:
        raise ValueError(f"Unknown operator: {operator}")
    if window_minutes < 120:
        raise ValueError("window_minutes must be at least 120 to obtain eight 15-minute intervals")
    if minimum_social_items < 1:
        raise ValueError("minimum_social_items must be positive")
    token = load_env().get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        if write_feed:
            feed_path, validation = _empty_output(output, "degraded")
            result = {"status": "AUTH_BLOCKED_NO_CREDENTIAL", "operator": operator, "department": department_value,
                      "feed_path": str(feed_path), "feed_validation": validation, "feed_system_status": "degraded"}
        else:
            result = {"status": "AUTH_BLOCKED_NO_CREDENTIAL", "operator": operator, "department": department_value,
                      "feed_path": None, "feed_validation": None, "feed_system_status": "degraded"}
        result["report_path"] = _write_report(result).relative_to(ROOT).as_posix()
        return result
    now = datetime.now(timezone.utc)
    department = resolve_department(department_value)
    if progress:
        progress("Resolviendo ubicación en Cloudflare")
    geo = resolve_cloudflare_geography(department, token)
    if geo.get("status") != "RESOLVED":
        result = {
            "status": "GEOGRAPHY_NOT_RESOLVED", "operator": operator, "department": department,
            "cloudflare_geography": geo, "run_at_utc": _format_utc(now), "feed_system_status": "degraded",
        }
        if write_feed:
            feed_path, validation = _empty_output(output, "degraded")
            result.update(feed_path=str(feed_path), feed_validation=validation)
        else:
            result.update(feed_path=None, feed_validation=None)
        result["report_path"] = _write_report(result).relative_to(ROOT).as_posix()
        return result
    if progress:
        progress("Consultando Cloudflare NetFlows")
    netflows = fetch_netflows(operator, ASNS[operator], str(geo["geo_id"]), window_minutes, token, now)
    if progress:
        progress("Consultando IODA por ASN")
    ioda = fetch_ioda(operator, ASNS[operator], window_minutes, now)
    from .ioda_geoasn import collect_geoasn
    from .radar_context import collect_radar_context

    if progress:
        progress("Consultando IODA por operador y región")
    ioda_geoasn = collect_geoasn(ASNS[operator], department, datetime.now(timezone.utc), window_minutes)
    if progress:
        progress("Consultando anomalías y anotaciones de Cloudflare Radar")
    radar = collect_radar_context(ASNS[operator], str(geo["geo_id"]), token, datetime.now(timezone.utc))
    if progress and use_news:
        progress("Evaluando noticias RSS")
    news = collect_news_corroboration(
        operator, department["code"], minimum_news_outlets, now, news_snapshot=news_snapshot,
    ) if use_news else None
    if progress and use_social:
        progress("Evaluando resultados sociales reales")
    social = collect_social_support(
        operator, department["code"], now, platforms=social_platforms,
        minimum_items=minimum_social_items, shared_summary=social_summary,
    ) if use_social else None
    osiptel_news = None
    if use_osiptel_news:
        from .osiptel_news import collect_osiptel_news

        if progress:
            progress("Consultando comunicados de OSIPTEL")
        osiptel_news = collect_osiptel_news()
    signals = build_signals(operator, department, technology, netflows, ioda, news, social)
    decision = assess(signals, datetime.now(timezone.utc))
    result: dict[str, Any] = {
        "status": "EVALUATED", "run_at_utc": _format_utc(now), "operator": operator,
        "asn": ASNS[operator], "department": department, "technology": technology,
        "cloudflare_geography": geo, "netflows": netflows, "ioda": ioda,
        "ioda_geoasn": ioda_geoasn, "radar_context": radar,
        "news": news, "social": social, "osiptel_news": osiptel_news, "signals": signals, "decision": decision,
        "netflows_rule": NETFLOWS_RULE, "max_signal_age_minutes": int(MAX_SIGNAL_AGE.total_seconds() / 60),
        "feed_path": None, "feed_validation": None,
    }
    if decision.get("status") == "QUALIFIED_FOR_SIMULATED_CREATIVE":
        state = "active" if confirm else "candidate"
        root = build_feed(
            decision, state=state, incident_type="degradation", system_status="ok",
            simulation_only=False, creative_url=creative_url,
        )
        result["feed_system_status"] = "ok"
        if write_feed:
            feed_path = output or LIVE_OUTPUT
            write_feed(root, feed_path)
            validation = validate_feed(feed_path)
            result["feed_path"] = str(feed_path)
            result["feed_validation"] = validation
            result["status"] = "FEED_WRITTEN" if validation.get("valid") else "FEED_INVALID"
        else:
            result["feed_root"] = root
    else:
        result["status"] = "SUPPRESSED"
        result["reasons"] = decision.get("reasons", [])
        degraded = netflows.get("http_status") != 200 or ioda.get("http_status") != 200 or radar.get("status") != "OK"
        result["feed_system_status"] = "degraded" if degraded else "ok"
        if write_feed:
            feed_path, validation = _empty_output(output, "degraded" if degraded else "ok")
            result["feed_path"] = str(feed_path)
            result["feed_validation"] = validation
            if not validation.get("valid"):
                result["status"] = "FEED_INVALID"
        else:
            result["feed_path"] = None
            result["feed_validation"] = None
    report_result = {key: value for key, value in result.items() if key != "feed_root"}
    result["report_path"] = _write_report(report_result).relative_to(ROOT).as_posix()
    return result


def run(
    operator: str, department_value: str, *, window_minutes: int = 180, technology: str = "internet_unspecified",
    use_news: bool = False, minimum_news_outlets: int = 2, use_social: bool = False,
    minimum_social_items: int = 1, social_platforms: list[str] | None = None, use_osiptel_news: bool = False,
    confirm: bool = False, creative_url: str | None = None, output: Path | None = None,
    social_summary: dict[str, Any] | None = None, news_snapshot: dict[str, Any] | None = None,
    progress=None, write_feed: bool = True,
) -> dict[str, Any]:
    try:
        return _run_once(
            operator, department_value, window_minutes=window_minutes, technology=technology,
            use_news=use_news, minimum_news_outlets=minimum_news_outlets,
            use_social=use_social, minimum_social_items=minimum_social_items,
            social_platforms=social_platforms, use_osiptel_news=use_osiptel_news,
            confirm=confirm, creative_url=creative_url, output=output,
            social_summary=social_summary, news_snapshot=news_snapshot,
            progress=progress, write_feed=write_feed,
        )
    except Exception as exc:
        if write_feed:
            try:
                path, validation = _empty_output(output, "degraded")
            except Exception as fallback_error:
                raise RuntimeError(f"failed to publish degraded XML: {fallback_error}") from exc
            result = {"status": "ERROR", "error": str(exc), "feed_path": str(path), "feed_validation": validation}
        else:
            result = {"status": "ERROR", "error": str(exc), "feed_path": None, "feed_validation": None}
        try:
            result["report_path"] = _write_report(result).relative_to(ROOT).as_posix()
        except OSError:
            pass
        return result


class _FeedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def _output_hint(argv: list[str]) -> Path | None:
    for index, argument in enumerate(argv):
        if argument.startswith("--output=") and argument[9:]:
            return Path(argument[9:])
        if argument == "--output" and index + 1 < len(argv) and not argv[index + 1].startswith("--"):
            return Path(argv[index + 1])
    return None


def main() -> None:
    parser = _FeedArgumentParser(description="Run one manual live evaluation and render the XML trigger feed when qualified")
    parser.add_argument("--operator", required=True, choices=sorted(ASNS))
    parser.add_argument("--department", required=True, help="Department name, 2-digit code or full UBIGEO")
    parser.add_argument("--window-minutes", type=int, default=180, help="Current/comparator window (minimum 120)")
    parser.add_argument("--technology", default="internet_unspecified", choices=["fixed", "mobile", "internet_unspecified"])
    parser.add_argument("--news-corroboration", action="store_true", help="Use fresh RSS candidates as supporting family (manual review still required)")
    parser.add_argument("--minimum-news-outlets", type=int, default=2)
    parser.add_argument("--social-corroboration", action="store_true", help="Use official-account posts/comments through Apify and TWEXAPI as supporting family")
    parser.add_argument("--minimum-social-items", type=int, default=1)
    parser.add_argument("--social-platforms", default="facebook,instagram,tiktok,x", help="Comma-separated social platforms")
    parser.add_argument("--osiptel-news", action="store_true", help="Collect official OSIPTEL news as review-only context")
    parser.add_argument("--confirm", action="store_true", help="Write state=active and trigger=true; otherwise write state=candidate")
    parser.add_argument("--creative-url", default=None)
    parser.add_argument("--output", default=None, help="XML output path; defaults to xml/trigger_feed_live.xml")
    try:
        args = parser.parse_args()
        social_platforms = [item.strip().casefold() for item in args.social_platforms.split(",") if item.strip()]
        result = run(
            args.operator, args.department, window_minutes=args.window_minutes, technology=args.technology,
            use_news=args.news_corroboration, minimum_news_outlets=args.minimum_news_outlets,
            use_social=args.social_corroboration, minimum_social_items=args.minimum_social_items,
            social_platforms=social_platforms, use_osiptel_news=args.osiptel_news,
            confirm=args.confirm, creative_url=args.creative_url,
            output=Path(args.output) if args.output else None,
        )
    except Exception as exc:
        try:
            path, _validation = _empty_output(_output_hint(sys.argv[1:]), "degraded")
            print(path.read_text(encoding="utf-8"))
        except Exception as fallback_error:
            print('<?xml version="1.0" encoding="UTF-8"?>')
            print(ET.tostring(build_empty_feed(datetime.now(timezone.utc), system_status="degraded"), encoding="unicode"))
            print(f"No se pudo reemplazar el archivo: {fallback_error}", file=sys.stderr)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    print(Path(result["feed_path"]).read_text(encoding="utf-8"))
    if result.get("status") in {"ERROR", "FEED_INVALID", "AUTH_BLOCKED_NO_CREDENTIAL", "GEOGRAPHY_NOT_RESOLVED"}:
        sys.exit(1)


if __name__ == "__main__":
    main()
