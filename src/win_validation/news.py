"""RSS-only candidate extraction for Peruvian news corroboration.

This module reads publisher feeds only. It never fetches article URLs. A match
is a reviewable news candidate, not an outage confirmation or activation rule.
"""
from __future__ import annotations

import csv
import html
import re
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
REPORTS = ROOT / "reports"
UBIGEO_PATH = ROOT / "data" / "ubigeo_hibrido.csv"

OUTLETS: list[dict[str, str]] = [
    {"outlet": name, "rank": "", "reach": "", "url": url, "status": "CONFIGURED_GLOBAL_FEED" if name == "Infobae" else "CONFIGURED"}
    for name, url in [
        ("RPP Noticias", "https://rpp.pe/rss"),
        ("El Comercio", "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml"),
        ("La República", "https://larepublica.pe/rss/home.xml"),
        ("América Noticias", "https://www.americatv.com.pe/noticias/feed"),
        ("Perú21", "https://peru21.pe/rss/"),
        ("Gestión", "https://gestion.pe/arc/outboundfeeds/rss/?outputType=xml"),
        ("Diario Correo", "https://diariocorreo.pe/arc/outboundfeeds/rss/?outputType=xml"),
        ("Trome", "https://trome.com/arc/outboundfeeds/rss/?outputType=xml"),
        ("Andina", "https://andina.pe/agencia/rss.aspx"),
        ("Exitosa Noticias", "https://exitosanoticias.pe/feed/"),
        ("Canal N", "https://canaln.pe/feed/"),
        ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml"),
        ("Bolognesi Noticias", "https://bolognesinoticias.com/feed/"),
        ("El Búho", "https://elbuho.pe/feed/"),
        ("Prensa Regional", "https://prensaregional.pe/feed/"),
        ("Los Andes", "https://losandes.com.pe/feed/"),
        ("Diario del Cusco", "https://diariodelcusco.pe/feed/"),
        ("Radio Onda Azul", "https://radioondaazul.com/feed/"),
        ("Diario Ahora Amazonía", "https://diarioahora.pe/feed/"),
        ("Diario Ahora Huánuco", "https://ahora.com.pe/feed/"),
        ("Tu Diario Huánuco", "https://tudiariohuanuco.pe/feed/"),
        ("Áncash Noticias", "https://ancashnoticias.com/feed/"),
        ("Huaraz Noticias", "https://huaraznoticias.com/feed/"),
        ("Diario La Opinión Ica", "https://diariolaopinion.pe/feed/"),
        ("Diario de Chimbote", "https://diariodechimbote.com/feed/"),
        ("Diario Voces", "https://diariovoces.com.pe/feed/"),
        ("Portal Ayacucho", "https://portalayacucho.com/feed/"),
        ("Página 3 Huánuco", "https://pagina3.pe/feed/"),
        ("Macro Norte", "https://macronorte.pe/feed/"),
        ("Walac Noticias", "https://walac.pe/feed/"),
        ("Diario del País", "https://delpais.com.pe/feed/"),
        ("Perú Informa", "https://www.peruinforma.com/feed/"),
        ("Grupo Panorama", "https://diariogrupopanorama.com/feed/"),
        ("DPL News", "https://dplnews.com/feed/"),
    ]
]

FEED_STATUS_FIELDS = [
    "outlet", "rank", "reach", "url", "status", "http_status", "parse_status",
    "feed_items", "news_candidates", "freshest_item_age_minutes", "evidence_id", "artifact_path",
]
CANDIDATE_FIELDS = [
    "outlet", "title", "published_at_utc", "age_minutes", "url", "internet_mentioned",
    "outage_language", "operators", "areas", "service_scope", "possibly_socially_derived",
    "news_candidate", "independence_status", "count_as_independent_family", "freshness_status",
    "source_id", "artifact_path",
]
RSS_FETCH_ATTEMPTS = 3
RSS_RETRY_BASE_SECONDS = 1.0
RSS_REQUEST_TIMEOUT_SECONDS = 12

OPERATOR_PATTERNS = {
    "movistar": (r"\bmovistar\b", r"\btelef[oó]nica\b"),
    "claro": (r"\bclaro\b",),
    "entel": (r"\bentel\b",),
    "bitel": (r"\bbitel\b", r"\bviettel\b"),
    "win": (r"\bwin\b", r"\bwi\s*net\b"),
}
INTERNET_RE = re.compile(r"\b(internet|fibra\s+[oó]ptica|banda\s+ancha|conexi[oó]n\s+a\s+internet)\b", re.I)
OUTAGE_RE = re.compile(
    r"\b(ca[ií]d[ao]|corte|interrupci[oó]n|sin\s+(?:el\s+)?(?:servicio|internet)|"
    r"fallas?|aver[ií]as?|problemas?|afectaci[oó]n|degradaci[oó]n|"
    r"restableci(?:miento|do)|no\s+funciona)\b",
    re.I,
)
SOCIAL_DERIVATION_RE = re.compile(
    r"\b(seg[uú]n\s+(?:los\s+)?usuarios|reportes?\s+de\s+usuarios|"
    r"usuarios\s+(?:reportan|indicaron|señalaron)|redes\s+sociales|"
    r"publicaciones?\s+en\s+(?:x|twitter|facebook)|quejas?\s+de\s+usuarios)\b",
    re.I,
)
FIXED_RE = re.compile(r"\b(fijo|residencial|fibra|hogar|casa)\b", re.I)
MOBILE_RE = re.compile(r"\b(m[oó]vil|celular|4g|5g|datos\s+m[oó]viles)\b", re.I)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_feed(xml_bytes: bytes) -> list[dict[str, str]]:
    """Parse RSS 2/1 and Atom metadata without requesting linked articles."""
    root = ET.fromstring(xml_bytes)
    entries = [element for element in root.iter() if _local(element.tag) in {"item", "entry"}]
    parsed: list[dict[str, str]] = []
    for entry in entries:
        fields: dict[str, str] = {}
        link = ""
        for child in entry:
            name = _local(child.tag)
            if name in {"title", "description", "summary", "encoded", "content", "subtitle"}:
                fields[name] = _clean_text(" ".join(child.itertext()))
            elif name in {"pubdate", "published", "updated", "date"} and not fields.get("published"):
                fields["published"] = _clean_text(" ".join(child.itertext()))
            elif name == "link":
                link = child.attrib.get("href", "") or _clean_text(" ".join(child.itertext()))
        title = fields.get("title", "")
        description = fields.get("encoded") or fields.get("content") or fields.get("description") or fields.get("summary", "")
        parsed.append({"title": title, "description": description, "published": fields.get("published", ""), "url": link})
    return parsed


def _normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _load_places() -> list[tuple[str, str, str, re.Pattern[str]]]:
    if not UBIGEO_PATH.exists():
        return []
    places: set[tuple[str, str, str, str]] = set()
    with UBIGEO_PATH.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            code = row.get("UBIGEO", "")
            for level, column, width in (("department", "DEPARTAMENTO", 2), ("province", "PROVINCIA", 4), ("district", "DISTRITO", 6)):
                label = (row.get(column) or "").strip()
                if len(label) >= 4 or (level == "district" and code == "150103" and _normalise(label) == "ate"):
                    places.add((level, code[:width], label, _normalise(label)))
    district_codes = {code for level, code, _label, _needle in places if level == "district"}
    if "150103" in district_codes:
        places.add(("district", "150103", "Ate", "santa clara"))
    if "150118" in district_codes:
        places.add(("district", "150118", "Lurigancho", "chosica"))
    return [
        (level, code, label, re.compile(
            rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
            + (r"(?!\s+clara\b)" if needle == "santa" else "")
        ))
        for level, code, label, needle in sorted(places, key=lambda item: len(item[3]), reverse=True)
    ]


def _area_mentions(text: str, places: list[tuple[str, str, str, re.Pattern[str]]]) -> list[dict[str, str]]:
    normalized = f" {_normalise(text)} "
    mentions: dict[tuple[str, str, str], dict[str, str]] = {}
    for level, code, label, pattern in places:
        if pattern.search(normalized):
            mentions[(level, code, label)] = {"level": level, "ubigeo": code, "name": label}
    return list(mentions.values())


def classify_item(
    item: dict[str, str], outlet: str, captured_at: datetime, places: list[tuple[str, str, str, re.Pattern[str]]],
) -> dict[str, Any]:
    text = f"{item.get('title', '')} {item.get('description', '')}".strip()
    published = _parse_datetime(item.get("published", ""))
    age_minutes = round((captured_at - published).total_seconds() / 60, 1) if published else None
    operators = [name for name, patterns in OPERATOR_PATTERNS.items() if any(re.search(pattern, text, re.I) for pattern in patterns)]
    internet_match = bool(INTERNET_RE.search(text))
    outage_match = bool(OUTAGE_RE.search(text))
    # Gazetteer matching is the expensive step; run it only after the much
    # cheaper internet + outage + operator gates have passed.
    areas = _area_mentions(text, places) if internet_match and outage_match and operators else []
    social_derived = bool(SOCIAL_DERIVATION_RE.search(text))
    fixed = bool(FIXED_RE.search(text))
    mobile = bool(MOBILE_RE.search(text))
    contexts = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
    aligned_context = any(
        INTERNET_RE.search(context) and OUTAGE_RE.search(context)
        and any(re.search(pattern, context, re.I) for patterns in OPERATOR_PATTERNS.values() for pattern in patterns)
        for context in contexts
    )
    candidate = bool(aligned_context and areas)
    return {
        "outlet": outlet,
        "title": item.get("title", ""),
        "published_at_utc": published.isoformat() if published else "",
        "age_minutes": age_minutes,
        "url": item.get("url", ""),
        "internet_mentioned": internet_match,
        "outage_language": outage_match,
        "operators": ";".join(operators),
        "areas": ";".join(f"{area['level']}:{area['name']}:{area['ubigeo']}" for area in areas),
        "service_scope": "fixed_and_mobile" if fixed and mobile else ("fixed" if fixed else ("mobile" if mobile else "unspecified")),
        "possibly_socially_derived": social_derived,
        "news_candidate": candidate,
        "independence_status": "POSSIBLY_SOCIAL_DERIVED" if social_derived else "NOT_REVIEWED",
        "count_as_independent_family": False,
        "freshness_status": "TIMESTAMP_MISSING" if age_minutes is None else ("FUTURE_TIMESTAMP" if age_minutes < -5 else "AGE_REQUIRES_ALIGNMENT"),
    }


def align_news_to_incident(
    item: dict[str, Any], operator: str, area_ubigeo: str,
    window_start: datetime, window_end: datetime,
) -> dict[str, Any]:
    """Align a parsed news candidate to one event without assuming independence.

    Geographic mentions can match the exact district or an official parent
    province/department. A separate source review is always required before
    the news item can be counted as an independent family.
    """
    published = _parse_datetime(str(item.get("published_at_utc", "")))
    normalized_operator = operator.casefold()
    item_operators = {part.strip().casefold() for part in str(item.get("operators", "")).split(";") if part.strip()}
    matches_area = False
    target = str(area_ubigeo).strip()
    for encoded in str(item.get("areas", "")).split(";"):
        try:
            level, _name, code = encoded.split(":", 2)
        except ValueError:
            continue
        prefix_length = {"department": 2, "province": 4, "district": 6}.get(level)
        if prefix_length and target[:prefix_length] == code:
            matches_area = True
            break
    time_match = published is not None and window_start <= published <= window_end
    candidate = bool(item.get("news_candidate"))
    aligned = candidate and normalized_operator in item_operators and matches_area and time_match
    social_derived = bool(item.get("possibly_socially_derived"))
    return {
        "aligned": aligned,
        "operator_match": normalized_operator in item_operators,
        "area_match": matches_area,
        "time_match": time_match,
        "possibly_socially_derived": social_derived,
        "independence_status": "POSSIBLY_SOCIAL_DERIVED" if social_derived else "NOT_REVIEWED",
        "independent_family_candidate": False,
        "requires_independence_review": aligned,
    }


def _fetch_feed(outlet: dict[str, str], slug: str) -> tuple[dict[str, Any], list[dict[str, str]], str]:
    """Fetch and parse one RSS feed, retrying transient failures only."""
    from .http import request

    last_record: dict[str, Any] = {}
    last_items: list[dict[str, str]] = []
    last_parse_status = "HTTP_ERROR"
    for attempt in range(1, RSS_FETCH_ATTEMPTS + 1):
        record, body = request(
            f"news_rss_{slug}", outlet["url"], "news_feed",
            user_agent="win-outage-validation/0.1 (RSS metadata reader; no article-page requests)",
            max_response_bytes=15_000_000,
            timeout=RSS_REQUEST_TIMEOUT_SECONDS,
        )
        status = record.get("http_status")
        try:
            items = parse_feed(body) if status == 200 else []
            parse_status = "XML_PARSED" if status == 200 else "HTTP_ERROR"
        except (ET.ParseError, ValueError):
            items = []
            parse_status = "XML_PARSE_ERROR"
        last_record, last_items, last_parse_status = record, items, parse_status
        transient_http = status is None or status == 429 or (isinstance(status, int) and status >= 500)
        retryable = transient_http or parse_status == "XML_PARSE_ERROR"
        if not retryable or attempt == RSS_FETCH_ATTEMPTS:
            break
        time.sleep(RSS_RETRY_BASE_SECONDS * attempt)
    return last_record, last_items, last_parse_status


def collect_news_snapshot() -> dict[str, Any]:
    """Fetch RSS once and return both the summary and candidate rows."""
    summary, candidates = _collect_current_news()
    return {"summary": summary, "candidates": candidates}


def collect_current_news() -> dict[str, Any]:
    """Fetch verified RSS endpoints, archive responses, and summarize candidates."""
    return collect_news_snapshot()["summary"]


def _collect_current_news() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    captured_at = datetime.now(timezone.utc)
    places = _load_places()
    feed_status_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for outlet in OUTLETS:
        if not outlet["url"]:
            feed_status_rows.append({**outlet, "http_status": "", "feed_items": 0, "news_candidates": 0, "freshest_item_age_minutes": "", "evidence_id": "", "artifact_path": ""})
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", _normalise(outlet["outlet"])).strip("_")
        record, items, parse_status = _fetch_feed(outlet, slug)
        classified = [classify_item(item, outlet["outlet"], captured_at, places) for item in items]
        candidates = [row for row in classified if row["news_candidate"]]
        valid_ages = [row["age_minutes"] for row in classified if row["age_minutes"] is not None and row["age_minutes"] >= 0]
        candidate_rows.extend({**row, "source_id": record.get("evidence_id", ""), "artifact_path": record.get("artifact_path", "")} for row in candidates)
        feed_status_rows.append({
            **outlet,
            "http_status": record.get("http_status", ""),
            "parse_status": parse_status,
            "feed_items": len(items),
            "news_candidates": len(candidates),
            "freshest_item_age_minutes": min(valid_ages) if valid_ages else "",
            "evidence_id": record.get("evidence_id", ""),
            "artifact_path": record.get("artifact_path", ""),
        })

    REPORTS.mkdir(exist_ok=True)
    feed_path = REPORTS / "current_news_feed_status.csv"
    candidate_path = REPORTS / "current_news_candidates.csv"
    for path, rows, fields in (
        (feed_path, feed_status_rows, FEED_STATUS_FIELDS),
        (candidate_path, candidate_rows, CANDIDATE_FIELDS),
    ):
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    configured_count = sum(bool(outlet["url"]) for outlet in OUTLETS)
    valid_count = sum(row.get("http_status") == 200 and row.get("parse_status") == "XML_PARSED" for row in feed_status_rows)
    summary = {
        "status": "COMPLETE" if valid_count == configured_count else "PARTIAL",
        "captured_at_utc": captured_at.isoformat(),
        "configured_feeds": configured_count,
        "feeds_http_200_xml": valid_count,
        "failed_feeds": [row["outlet"] for row in feed_status_rows if row.get("url") and not (row.get("http_status") == 200 and row.get("parse_status") == "XML_PARSED")],
        "candidate_items": len(candidate_rows),
        "independent_candidate_items": 0,
        "socially_derived_candidate_items": sum(bool(row["possibly_socially_derived"]) for row in candidate_rows),
        "feeds_report": feed_path.relative_to(ROOT).as_posix(),
        "candidates_report": candidate_path.relative_to(ROOT).as_posix(),
        "note": "RSS metadata only; no article URLs fetched. Candidate status is not outage confirmation or activation authorization.",
    }
    return summary, candidate_rows
