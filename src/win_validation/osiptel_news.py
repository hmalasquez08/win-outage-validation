"""Collect OSIPTEL's public news listing as review-only context."""
from __future__ import annotations

import json
import re
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .http import request
from .news import INTERNET_RE, OPERATOR_PATTERNS, OUTAGE_RE, REPORTS, ROOT, _area_mentions, _load_places

LISTING_URL = "https://www.osiptel.gob.pe/portal-del-usuario/noticias/"


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, set[str]]] = []
        self.current: dict[str, str] | None = None
        self.card_depth = 0
        self.items: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        self.stack.append((tag, classes))
        if tag == "div" and "card-noticias" in classes and self.current is None:
            self.current = {"title": "", "date": "", "description": "", "url": ""}
            self.card_depth = len(self.stack)
        if self.current is not None and tag == "a" and not self.current["url"]:
            href = values.get("href") or ""
            if "/noticias/" in href:
                self.current["url"] = urllib.parse.urljoin(LISTING_URL, href)
        if tag in {"img", "br", "hr", "input", "meta", "link", "source", "area", "wbr", "embed", "param", "track", "base", "col"}:
            self.stack.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in {"img", "br", "hr", "input", "meta", "link", "source", "area", "wbr", "embed", "param", "track", "base", "col"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                if self.current is not None and index + 1 == self.card_depth:
                    if self.current["title"] and self.current["url"]:
                        self.items.append({key: re.sub(r"\s+", " ", value).strip() for key, value in self.current.items()})
                    self.current = None
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        if any("card-title" in classes for _, classes in self.stack):
            field = "title"
        elif any("card-fecha" in classes for _, classes in self.stack):
            field = "date"
        elif any("card_extract" in classes for _, classes in self.stack):
            field = "description"
        else:
            return
        self.current[field] += data + " "


def parse_listing(body: bytes) -> list[dict[str, str]]:
    parser = _ListingParser()
    parser.feed(body.decode("utf-8-sig", errors="replace"))
    return parser.items


def collect_osiptel_news() -> dict[str, Any]:
    record, body = request("osiptel_news_listing", LISTING_URL, "official_news", timeout=20)
    items = parse_listing(body) if record.get("http_status") == 200 else []
    places = _load_places()
    candidates: list[dict[str, Any]] = []
    for item in items:
        text = f"{item['title']} {item['description']}"
        internet = bool(INTERNET_RE.search(text))
        outage = bool(OUTAGE_RE.search(text))
        if not (internet or outage):
            continue
        operators = [name for name, patterns in OPERATOR_PATTERNS.items() if any(re.search(pattern, text, re.I) for pattern in patterns)]
        areas = _area_mentions(text, places) if operators and internet and outage else []
        candidates.append({
            **item, "internet_mentioned": internet, "outage_language": outage,
            "operators": operators, "areas": areas,
            "freshness_status": "DATE_ONLY_NOT_ELIGIBLE", "eligible_for_signal": False,
            "source_id": record.get("evidence_id"), "artifact_path": record.get("artifact_path"),
        })
    status = "HTTP_ERROR" if record.get("http_status") != 200 else ("PARSED" if items else "PARSE_EMPTY")
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / "osiptel_news_latest.json"
    result: dict[str, Any] = {
        "status": status, "http_status": record.get("http_status"),
        "observed_at_utc": record.get("observed_at_utc"), "listing_url": LISTING_URL,
        "items": len(items), "candidates": candidates, "report_path": path.relative_to(ROOT).as_posix(),
        "note": "Official listing metadata; date-only publications are review context and cannot become fresh signals.",
    }
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
