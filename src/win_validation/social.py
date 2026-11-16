"""Social-source corroboration for Peruvian ISP complaints.

The collector reads public posts and comments from the official operator
accounts. It is opt-in, corroboration-only and never activates a campaign.
"""
from __future__ import annotations

import csv
import json
import re
import urllib.parse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .creative_trigger import MAX_FUTURE_SKEW, MAX_SIGNAL_AGE
from .http import request
from .news import (
    FIXED_RE,
    INTERNET_RE,
    MOBILE_RE,
    OPERATOR_PATTERNS,
    OUTAGE_RE,
    _area_mentions,
    _load_places,
    _parse_datetime,
)

ROOT = Path.cwd()
REPORTS = ROOT / "reports"
APIFY_API = "https://api.apify.com/v2"

DEFAULT_PLATFORMS = ("facebook", "instagram", "tiktok", "x")
SOCIAL_ACCOUNTS: dict[str, dict[str, str]] = {
    "movistar": {
        "facebook": "https://www.facebook.com/movistarperu",
        "instagram": "https://www.instagram.com/movistarperu/",
        "tiktok": "https://www.tiktok.com/@movistarperu_oficial",
        "x": "https://x.com/MovistarPeru",
    },
    "claro": {
        "facebook": "https://www.facebook.com/AmericaMovilPeruSAC",
        "instagram": "https://www.instagram.com/claroperu/",
        "tiktok": "https://www.tiktok.com/@claro_peru",
        "x": "https://x.com/claroperu",
    },
    "entel": {
        "facebook": "https://www.facebook.com/EntelPeru",
        "instagram": "https://www.instagram.com/Entel_Peru/",
        "tiktok": "https://www.tiktok.com/@entel_peru",
        "x": "https://x.com/EntelPeru",
    },
    "bitel": {
        "facebook": "https://www.facebook.com/BitelPeru",
        "instagram": "https://www.instagram.com/bitel_peru/",
        "tiktok": "https://www.tiktok.com/@bitel_peru",
        "x": "https://x.com/bitelperu",
    },
    "osiptel": {
        "facebook": "https://www.facebook.com/OsiptelOficial",
        "instagram": "https://www.instagram.com/osipteloficial/",
        "x": "https://x.com/OSIPTEL",
    },
    "rpp_noticias": {
        "facebook": "https://www.facebook.com/rppnoticias/",
        "instagram": "https://www.instagram.com/rppnoticias/",
        "tiktok": "https://www.tiktok.com/@rppnoticias",
        "x": "https://x.com/RPPNoticias",
    },
    "diario_correo": {
        "facebook": "https://www.facebook.com/CorreoPeru/",
        "instagram": "https://www.instagram.com/diario_correo/",
        "x": "https://x.com/diariocorreo",
    },
}
NEWS_ACCOUNTS = {"rpp_noticias", "diario_correo"}

ACTORS = {
    "facebook_posts": "apify~facebook-posts-scraper",
    "facebook_comments": "apify~facebook-comments-scraper",
    "instagram": "apify~instagram-scraper",
    "tiktok_posts": "clockworks~tiktok-scraper",
    "tiktok_comments": "clockworks~tiktok-comments-scraper",
}

SOCIAL_CANDIDATE_FIELDS = [
    "operator", "platform", "account_url", "item_type", "platform_item_id", "author",
    "text", "published_at_utc", "age_minutes", "url", "parent_url", "internet_mentioned",
    "outage_language", "mentioned_operators", "content_match", "areas", "service_scope", "social_candidate",
    "independence_status", "count_as_independent_family", "freshness_status", "source_id",
    "artifact_path",
]


class SocialError(RuntimeError):
    def __init__(self, message: str, record: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.record = record or {}


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _nested(item: dict[str, Any], path: str) -> Any:
    current: Any = item
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def _tiktok_handle(account_url: str) -> str:
    return account_url.rstrip("/").rsplit("@", 1)[-1]


def _x_handle(account_url: str) -> str:
    return account_url.rstrip("/").rsplit("/", 1)[-1]


def _post_time(item: dict[str, Any]) -> datetime | None:
    raw = _first(item, ("createTimeISO", "time", "timestamp", "createdAt", "date", "created_at", "create_time"))
    if raw is None:
        return None
    if isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.strip().isdigit()):
        numeric = float(raw)
        if numeric > 10_000_000_000:
            numeric /= 1000
        try:
            parsed = datetime.fromtimestamp(numeric, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        parsed = _parse_datetime(str(raw))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _item_url(item: dict[str, Any], platform: str, item_type: str) -> str:
    if item_type == "comment":
        keys = {
            "facebook": ("commentUrl", "url"),
            "instagram": ("commentUrl", "url"),
            "tiktok": ("videoWebUrl", "url"),
            "x": ("url", "twitterUrl"),
        }
    else:
        keys = {
            "facebook": ("url",),
            "instagram": ("url",),
            "tiktok": ("webVideoUrl", "url"),
            "x": ("url", "twitterUrl"),
        }
    return _text(_first(item, keys.get(platform, ("url",))))


def _parent_url(item: dict[str, Any], platform: str) -> str:
    keys = {
        "facebook": ("facebookUrl", "postUrl"),
        "instagram": ("postUrl",),
        "tiktok": ("videoWebUrl", "postUrl"),
        "x": ("conversationUrl", "postUrl"),
    }
    return _text(_first(item, keys.get(platform, ("postUrl",))))


def _item_id(item: dict[str, Any], platform: str) -> str:
    keys = {
        "facebook": ("commentId", "postId", "id"),
        "instagram": ("id", "shortCode"),
        "tiktok": ("cid", "id"),
        "x": ("id", "tweetId"),
    }
    return _text(_first(item, keys.get(platform, ("id",))))


def _author(item: dict[str, Any], platform: str) -> str:
    keys = {
        "facebook": ("profileName", "user.name", "authorName", "name"),
        "instagram": ("ownerUsername", "owner.username", "username"),
        "tiktok": ("authorMeta.name", "authorMeta.uniqueId", "uniqueId", "author"),
        "x": ("author.userName", "author.username", "username"),
    }
    for key in keys.get(platform, ("author",)):
        value = _nested(item, key) if "." in key else item.get(key)
        if value not in (None, ""):
            return _text(value)
    return ""


def _item_text(item: dict[str, Any]) -> str:
    for key in ("text", "caption", "message", "description", "title"):
        value = item.get(key)
        if value not in (None, ""):
            return _text(value)
    return ""


def _normalize_item(
    item: dict[str, Any], operator: str, platform: str, account_url: str, item_type: str,
) -> dict[str, Any]:
    return {
        "operator": operator,
        "platform": platform,
        "account_url": account_url,
        "item_type": item_type,
        "platform_item_id": _item_id(item, platform),
        "author": _author(item, platform),
        "text": _item_text(item),
        "published_at": _post_time(item),
        "url": _item_url(item, platform, item_type),
        "parent_url": _parent_url(item, platform),
    }


def _area_matches(areas: str, department_code: str) -> bool:
    for encoded in areas.split(";"):
        try:
            _level, _name, code = encoded.split(":", 2)
        except ValueError:
            continue
        if code.strip()[:2] == department_code:
            return True
    return False


def _classify(
    item: dict[str, Any], captured_at: datetime, places: list[tuple[str, str, str, re.Pattern[str]]],
    source_id: str, artifact_path: str,
) -> dict[str, Any]:
    text = item.get("text", "")
    published = item.get("published_at")
    age_minutes = round((captured_at - published).total_seconds() / 60, 1) if published else None
    internet_match = bool(INTERNET_RE.search(text))
    outage_match = bool(OUTAGE_RE.search(text))
    mentioned_operators = [
        name for name, patterns in OPERATOR_PATTERNS.items()
        if any(re.search(pattern, text, re.I) for pattern in patterns)
    ]
    account_operator_match = item["operator"] in NEWS_ACCOUNTS | {"osiptel"} or not mentioned_operators or item["operator"] in mentioned_operators
    areas = _area_mentions(text, places) if internet_match and outage_match and account_operator_match else []
    content_match = internet_match and outage_match and bool(areas) and account_operator_match
    fixed = bool(FIXED_RE.search(text))
    mobile = bool(MOBILE_RE.search(text))
    if age_minutes is None:
        freshness = "TIMESTAMP_MISSING"
    elif age_minutes < -MAX_FUTURE_SKEW.total_seconds() / 60:
        freshness = "FUTURE_TIMESTAMP"
    elif age_minutes > MAX_SIGNAL_AGE.total_seconds() / 60:
        freshness = "STALE"
    else:
        freshness = "FRESH"
    candidate = content_match and freshness == "FRESH"
    return {
        "operator": item["operator"],
        "platform": item["platform"],
        "account_url": item["account_url"],
        "item_type": item["item_type"],
        "platform_item_id": item["platform_item_id"],
        "author": item["author"],
        "text": text,
        "published_at_utc": _iso(published) if published else "",
        "age_minutes": age_minutes,
        "url": item["url"],
        "parent_url": item["parent_url"],
        "internet_mentioned": internet_match,
        "outage_language": outage_match,
        "mentioned_operators": ";".join(mentioned_operators),
        "content_match": content_match,
        "areas": ";".join(f"{area['level']}:{area['name']}:{area['ubigeo']}" for area in areas),
        "service_scope": "fixed_and_mobile" if fixed and mobile else ("fixed" if fixed else ("mobile" if mobile else "unspecified")),
        "social_candidate": candidate,
        "independence_status": "SOCIAL_ACCOUNT_CONTEXT",
        "count_as_independent_family": False,
        "freshness_status": freshness,
        "source_id": source_id,
        "artifact_path": artifact_path,
    }


def _posts_call(platform: str, account_url: str, max_posts: int) -> tuple[str, dict[str, Any]]:
    if platform == "facebook":
        return ACTORS["facebook_posts"], {"startUrls": [{"url": account_url}], "resultsLimit": max_posts}
    if platform == "instagram":
        return ACTORS["instagram"], {"resultsType": "posts", "directUrls": [account_url], "resultsLimit": max_posts}
    if platform == "tiktok":
        return ACTORS["tiktok_posts"], {"profiles": [_tiktok_handle(account_url)], "resultsPerPage": max_posts, "profileSorting": "latest"}
    raise ValueError(f"Unsupported platform: {platform}")


def _comments_call(
    platform: str, account_url: str, post_urls: list[str], max_posts: int, max_comments: int,
) -> tuple[str, dict[str, Any]]:
    if platform == "facebook":
        return ACTORS["facebook_comments"], {"startUrls": [{"url": url} for url in post_urls], "resultsLimit": max_comments}
    if platform == "instagram":
        return ACTORS["instagram"], {"resultsType": "comments", "directUrls": post_urls, "resultsLimit": max_comments}
    if platform == "tiktok":
        return ACTORS["tiktok_comments"], {
            "profiles": [_tiktok_handle(account_url)], "resultsPerPage": max_posts,
            "commentsPerPost": max_comments, "profileSorting": "latest",
        }
    raise ValueError(f"Unsupported platform: {platform}")


def _run_actor(actor: str, actor_input: dict[str, Any], token: str, timeout: int, max_total_charge_usd: Decimal | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = f"{APIFY_API}/acts/{actor}/run-sync-get-dataset-items?format=json&clean=true"
    if max_total_charge_usd is not None:
        url += "&" + urllib.parse.urlencode({"maxTotalChargeUsd": str(max_total_charge_usd), "timeout": timeout})
    record, body = request(
        f"social_apify_{actor}", url, "social_apify", token=token,
        method="POST", payload=actor_input, timeout=timeout, max_response_bytes=25_000_000,
    )
    if record.get("http_status") not in (200, 201):
        try:
            error = json.loads(body).get("error", {})
            if isinstance(error, dict) and isinstance(error.get("type"), str):
                record["apify_error_type"] = error["type"]
        except (ValueError, TypeError, AttributeError):
            pass
        raise SocialError(f"Apify actor failed: {actor}", record)
    try:
        items = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SocialError(f"Apify dataset is not JSON: {actor}", record) from exc
    if not isinstance(items, list):
        raise SocialError(f"Apify dataset is not a list: {actor}", record)
    return [item for item in items if isinstance(item, dict)], record


class _ApifyCredentialPool:
    """Distribute actor calls without retrying runs that may have started."""

    def __init__(self, env: dict[str, str]) -> None:
        primary = "APIFY_TOKEN" if env.get("APIFY_TOKEN", "").strip() else "APIFY"
        self._credentials: list[tuple[str, str]] = []
        seen: set[str] = set()
        for name in (primary, "APIFY_2", "APIFY_3", "APIFY_4", "APIFY_5"):
            token = env.get(name, "").strip()
            if token and token not in seen:
                self._credentials.append((name, token))
                seen.add(token)
        self._next = 0
        self.last_slot: str | None = None
        self.rejected_slots: list[str] = []

    def __bool__(self) -> bool:
        return bool(self._credentials)

    def run(self, actor: str, actor_input: dict[str, Any], timeout: int, budget: "ApifyBudget | None" = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        attempted: set[str] = set()
        last_error: SocialError | None = None
        while self._credentials and len(attempted) < len(self._credentials):
            index = self._next % len(self._credentials)
            slot, token = self._credentials[index]
            if slot in attempted:
                self._next = (index + 1) % len(self._credentials)
                continue
            attempted.add(slot)
            self.last_slot = slot
            try:
                if budget is None:
                    result = _run_actor(actor, actor_input, token, timeout)
                else:
                    result = _run_actor(actor, actor_input, token, timeout, budget.reserve(actor))
                self._next = (index + 1) % len(self._credentials)
                return result
            except SocialError as exc:
                last_error = exc
                status = exc.record.get("http_status")
                error_type = exc.record.get("apify_error_type")
                if status == 401:
                    self.rejected_slots.append(slot)
                    self._credentials.pop(index)
                    attempted.discard(slot)
                    if self._credentials:
                        self._next = index % len(self._credentials)
                elif status in (402, 403, 429) or error_type in {
                    "not-enough-usage-to-run-paid-actor", "monthly-usage-limit-too-low",
                    "max-total-charge-usd-below-minimum", "user-plan-not-allowed-for-coupon",
                }:
                    self._next = (index + 1) % len(self._credentials)
                else:
                    self._next = (index + 1) % len(self._credentials)
                    raise
        if last_error is not None:
            raise last_error
        raise SocialError("No valid Apify credentials remain", {"http_status": 401})


class ApifyBudget:
    """Conservative sum of per-run Actor charge limits across all accounts."""

    def __init__(self, amount_usd: str) -> None:
        try:
            self.limit = Decimal(amount_usd)
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("Invalid Apify budget") from exc
        if not self.limit.is_finite() or self.limit <= 0:
            raise ValueError("Apify budget must be positive and finite")
        self.reserved = Decimal("0")
        self.exhausted = False

    def reserve(self, actor: str) -> Decimal:
        cap = Decimal("0.50") if actor == ACTORS["tiktok_posts"] else Decimal("0.05")
        if self.reserved + cap > self.limit:
            self.exhausted = True
            raise SocialError("Apify budget exhausted before actor launch", {"http_status": None, "budget_exhausted": True})
        self.reserved += cap
        return cap


def _collect_twex_account(
    operator: str, account_url: str, token: str, max_posts: int, max_comments: int,
    timeout: int, places: list, rows: list[dict[str, Any]], seen: set,
    calls: list[dict[str, Any]], failures: list[dict[str, Any]], progress=None,
) -> bool:
    from .twexapi import TwexError, replies, timeline

    handle = _x_handle(account_url)
    if progress:
        progress(f"TWEXAPI: {operator} / x / publicaciones")
    call = {"operator": operator, "platform": "x", "phase": "posts", "provider": "twexapi"}
    calls.append(call)
    try:
        posts, record = timeline(handle, token, max_posts=max_posts, timeout=min(timeout, 30))
    except TwexError as exc:
        call["http_status"] = exc.record.get("http_status")
        call["api_code"] = exc.record.get("api_code")
        failures.append({**call, "error": str(exc), "evidence_id": exc.record.get("evidence_id")})
        return exc.record.get("http_status") not in (401, 403, 429) and exc.record.get("api_code") not in (401, 403, 429)
    call.update(http_status=record.get("http_status"), returned=len(posts), has_next_page=record.get("has_next_page"))
    for item in posts:
        normalized = _normalize_item(item, operator, "x", account_url, "post")
        classified = _classify(normalized, datetime.now(timezone.utc), places, record.get("evidence_id", ""), record.get("artifact_path", ""))
        key = ("x", operator, "post:" + (classified["platform_item_id"] or classified["url"]))
        if classified["internet_mentioned"] and key not in seen:
            seen.add(key)
            rows.append(classified)
    remaining = max_comments
    for post in posts:
        if remaining <= 0:
            break
        if progress:
            progress(f"TWEXAPI: {operator} / x / respuestas")
        call = {"operator": operator, "platform": "x", "phase": "comments", "provider": "twexapi"}
        calls.append(call)
        try:
            items, reply_record = replies(post["tweetId"], post["url"], token, max_replies=remaining, timeout=min(timeout, 30))
        except TwexError as exc:
            call["http_status"] = exc.record.get("http_status")
            call["api_code"] = exc.record.get("api_code")
            failures.append({**call, "error": str(exc), "evidence_id": exc.record.get("evidence_id")})
            if exc.record.get("http_status") in (401, 403, 429) or exc.record.get("api_code") in (401, 403, 429):
                return False
            continue
        call.update(http_status=reply_record.get("http_status"), returned=len(items), has_next_page=reply_record.get("has_next_page"))
        remaining -= len(items)
        for item in items:
            normalized = _normalize_item(item, operator, "x", account_url, "comment")
            classified = _classify(normalized, datetime.now(timezone.utc), places, reply_record.get("evidence_id", ""), reply_record.get("artifact_path", ""))
            key = ("x", operator, "comment:" + (classified["platform_item_id"] or classified["url"]))
            if classified["internet_mentioned"] and key not in seen:
                seen.add(key)
                rows.append(classified)
    return True


def _write_reports(rows: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[Path, Path]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    candidate_path = REPORTS / "social_candidates.csv"
    with candidate_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOCIAL_CANDIDATE_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in SOCIAL_CANDIDATE_FIELDS} for row in rows)
    run_path = REPORTS / "social_run_latest.json"
    run_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return candidate_path, run_path


def collect_social_evidence(
    operators: list[str] | None = None, platforms: list[str] | None = None, *,
    max_posts: int = 3, max_comments: int = 10, timeout: int = 300, dry_run: bool = False,
    budget: ApifyBudget | None = None, progress=None,
) -> dict[str, Any]:
    """Collect social complaint candidates through Apify and TWEXAPI."""
    selected_operators = list(SOCIAL_ACCOUNTS if operators is None else operators)
    selected_platforms = list(DEFAULT_PLATFORMS if platforms is None else platforms)
    if not selected_operators or not selected_platforms:
        raise ValueError("At least one operator and one platform are required")
    if max_posts < 1 or max_comments < 1 or timeout < 1:
        raise ValueError("max_posts, max_comments and timeout must be positive")
    for operator in selected_operators:
        if operator not in SOCIAL_ACCOUNTS:
            raise ValueError(f"Unknown operator: {operator}")
    for platform in selected_platforms:
        if platform not in DEFAULT_PLATFORMS:
            raise ValueError(f"Unknown platform: {platform}")
    captured_at = datetime.now(timezone.utc)
    if dry_run:
        calls = []
        for operator in selected_operators:
            for platform in selected_platforms:
                if platform not in SOCIAL_ACCOUNTS[operator]:
                    continue
                account_url = SOCIAL_ACCOUNTS[operator][platform]
                if platform == "x":
                    calls.append({"operator": operator, "platform": platform, "phase": "posts", "provider": "twexapi", "handle": _x_handle(account_url), "max_posts": max_posts})
                    calls.append({"operator": operator, "platform": platform, "phase": "comments", "provider": "twexapi", "tweet_ids": "<from-posts-phase>", "max_comments": max_comments})
                    continue
                actor, actor_input = _posts_call(platform, account_url, max_posts)
                calls.append({"operator": operator, "platform": platform, "phase": "posts", "actor": actor, "input": actor_input})
                comments_actor, comments_input = _comments_call(platform, account_url, ["<post-urls-from-posts-phase>"], max_posts, max_comments)
                calls.append({"operator": operator, "platform": platform, "phase": "comments", "actor": comments_actor, "input": comments_input})
        summary = {
            "status": "DRY_RUN", "captured_at_utc": _iso(captured_at), "operators": selected_operators,
            "platforms": selected_platforms,
            "actor_calls": sum(call.get("provider") != "twexapi" for call in calls),
            "twexapi_calls": sum(call.get("provider") == "twexapi" for call in calls), "calls": calls,
            "note": "No Apify or TWEXAPI request was executed and no credit was consumed.",
        }
        REPORTS.mkdir(parents=True, exist_ok=True)
        (REPORTS / "social_dry_run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    from .http import load_env

    env = load_env()
    credentials = _ApifyCredentialPool(env)
    twex_token = (env.get("TWEXAPI_API_KEY") or env.get("X_API_SCRAPER_KEY") or "").strip()
    if not credentials and not twex_token:
        return {"status": "AUTH_BLOCKED_NO_CREDENTIAL", "captured_at_utc": _iso(captured_at)}

    places = _load_places()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    auth_blocked = not bool(credentials)
    twex_available = bool(twex_token)
    for operator in selected_operators:
        for platform in selected_platforms:
            if platform not in SOCIAL_ACCOUNTS[operator]:
                continue
            account_url = SOCIAL_ACCOUNTS[operator][platform]
            if platform == "x":
                if not twex_available:
                    failures.append({"operator": operator, "platform": "x", "phase": "posts", "provider": "twexapi", "error": "TWEXAPI_AUTH_UNAVAILABLE"})
                    continue
                twex_available = _collect_twex_account(
                    operator, account_url, twex_token, max_posts, max_comments, timeout,
                    places, rows, seen, calls, failures, progress,
                )
                continue
            if auth_blocked or (budget is not None and budget.exhausted):
                failures.append({"operator": operator, "platform": platform, "phase": "posts", "provider": "apify", "error": "APIFY_AUTH_UNAVAILABLE" if auth_blocked else "APIFY_BUDGET_EXHAUSTED"})
                continue
            posts_actor, posts_input = _posts_call(platform, account_url, max_posts)
            if progress:
                progress(f"Apify: {operator} / {platform} / publicaciones")
            try:
                calls.append({"operator": operator, "platform": platform, "phase": "posts", "actor": posts_actor})
                post_items, post_record = credentials.run(posts_actor, posts_input, timeout, budget)
            except SocialError as exc:
                failures.append({
                    "operator": operator, "platform": platform, "phase": "posts",
                    "actor": posts_actor, "http_status": exc.record.get("http_status"),
                    "error": str(exc), "evidence_id": exc.record.get("evidence_id"),
                })
                calls[-1]["http_status"] = exc.record.get("http_status")
                calls[-1]["credential_slot"] = credentials.last_slot
                auth_blocked = not credentials
                continue
            calls[-1]["http_status"] = post_record.get("http_status")
            calls[-1]["credential_slot"] = credentials.last_slot
            normalized_posts = [
                _normalize_item(item, operator, platform, account_url, "post")
                for item in post_items
            ]
            post_urls = [item["url"] for item in normalized_posts if item["url"]][:max_posts]
            classified_posts = []
            for item in normalized_posts:
                classified = _classify(item, datetime.now(timezone.utc), places, post_record.get("evidence_id", ""), post_record.get("artifact_path", ""))
                if classified["internet_mentioned"]:
                    classified_posts.append(classified)
            for classified in classified_posts:
                key = (platform, operator, classified["item_type"] + ":" + (classified["platform_item_id"] or classified["url"]))
                if key not in seen:
                    seen.add(key)
                    rows.append(classified)

            if platform in {"facebook", "instagram", "x"} and not post_urls:
                failures.append({
                    "operator": operator, "platform": platform, "phase": "comments",
                    "actor": "", "http_status": "", "error": "NO_POST_URLS",
                })
                continue
            comments_actor, comments_input = _comments_call(platform, account_url, post_urls, max_posts, max_comments)
            if progress:
                progress(f"Apify: {operator} / {platform} / comentarios")
            try:
                calls.append({"operator": operator, "platform": platform, "phase": "comments", "actor": comments_actor})
                comment_items, comment_record = credentials.run(comments_actor, comments_input, timeout, budget)
            except SocialError as exc:
                failures.append({
                    "operator": operator, "platform": platform, "phase": "comments",
                    "actor": comments_actor, "http_status": exc.record.get("http_status"),
                    "error": str(exc), "evidence_id": exc.record.get("evidence_id"),
                })
                calls[-1]["http_status"] = exc.record.get("http_status")
                calls[-1]["credential_slot"] = credentials.last_slot
                auth_blocked = not credentials
                continue
            calls[-1]["http_status"] = comment_record.get("http_status")
            calls[-1]["credential_slot"] = credentials.last_slot
            normalized_comments = [
                _normalize_item(item, operator, platform, account_url, "comment")
                for item in comment_items
            ]
            for item in normalized_comments:
                classified = _classify(item, datetime.now(timezone.utc), places, comment_record.get("evidence_id", ""), comment_record.get("artifact_path", ""))
                if not classified["internet_mentioned"]:
                    continue
                key = (platform, operator, classified["item_type"] + ":" + (classified["platform_item_id"] or classified["url"]))
                if key not in seen:
                    seen.add(key)
                    rows.append(classified)

    candidate_count = sum(bool(row.get("social_candidate")) for row in rows)
    summary: dict[str, Any] = {
        "status": "PARTIAL" if failures else "COMPLETE",
        "captured_at_utc": _iso(captured_at),
        "operators": selected_operators,
        "platforms": selected_platforms,
        "max_posts": max_posts,
        "max_comments": max_comments,
        "actor_calls": sum(call.get("provider") != "twexapi" for call in calls),
        "twexapi_calls": sum(call.get("provider") == "twexapi" for call in calls),
        "actor_failures": failures,
        "rejected_credential_slots": credentials.rejected_slots,
        "budget_limit_usd": str(budget.limit) if budget is not None else None,
        "budget_reserved_usd": str(budget.reserved) if budget is not None else None,
        "budget_exhausted": budget.exhausted if budget is not None else False,
        "items": len(rows),
        "candidate_items": candidate_count,
        "calls": calls,
        "note": "Social posts and comments use Apify and TWEXAPI as applicable and are corroboration only; they never trigger alone.",
    }
    candidate_path, run_path = _write_reports(rows, summary)
    summary["candidates_report"] = candidate_path.relative_to(ROOT).as_posix()
    summary["run_report"] = run_path.relative_to(ROOT).as_posix()
    run_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return summary


def collect_social_corroboration(
    operator: str, department_code: str, now: datetime, *, platforms: list[str] | None = None,
    minimum_items: int = 1, max_posts: int = 3, max_comments: int = 10, timeout: int = 300,
    shared_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = shared_summary if shared_summary is not None else collect_social_evidence(
        operators=[operator, "osiptel", *sorted(NEWS_ACCOUNTS)], platforms=platforms, max_posts=max_posts,
        max_comments=max_comments, timeout=timeout,
    )
    path = REPORTS / "social_candidates.csv"
    rows: list[dict[str, str]] = []
    if summary.get("candidates_report") and path.exists():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    matched: list[dict[str, str]] = []
    news_context: list[dict[str, str]] = []
    evaluated_at = max(now, datetime.now(timezone.utc))
    for row in rows:
        if row.get("social_candidate", "").casefold() != "true":
            continue
        source = row.get("operator", "").casefold()
        mentioned = {value.strip().casefold() for value in row.get("mentioned_operators", "").split(";")}
        if source != operator and not (source in NEWS_ACCOUNTS | {"osiptel"} and operator in mentioned):
            continue
        if not _area_matches(row.get("areas", ""), department_code):
            continue
        published = _parse_datetime(row.get("published_at_utc", ""))
        if published is None:
            continue
        age = evaluated_at - published
        if age > MAX_SIGNAL_AGE or age < -MAX_FUTURE_SKEW:
            continue
        if source in NEWS_ACCOUNTS:
            news_context.append(row)
        else:
            matched.append(row)
    return {
        "summary": summary,
        "candidates_report": path.relative_to(ROOT).as_posix() if path.exists() else None,
        "matched": matched,
        "news_context": news_context,
        "platforms": sorted({row.get("platform", "") for row in matched if row.get("platform")}),
        "minimum_items": minimum_items,
        "eligible": len(matched) >= minimum_items,
    }


def _split(value: str) -> list[str]:
    return [item.strip().casefold() for item in value.split(",") if item.strip()]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Collect social corroboration from official operator accounts")
    parser.add_argument("--operators", default=",".join(SOCIAL_ACCOUNTS), help="Comma-separated operator names")
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS), help="Comma-separated platforms")
    parser.add_argument("--max-posts", type=int, default=3)
    parser.add_argument("--max-comments", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=300, help="Seconds per Apify actor call")
    parser.add_argument("--dry-run", action="store_true", help="Print the actor plan without spending Apify credit")
    args = parser.parse_args()
    try:
        summary = collect_social_evidence(
            operators=_split(args.operators), platforms=_split(args.platforms),
            max_posts=args.max_posts, max_comments=args.max_comments,
            timeout=args.timeout, dry_run=args.dry_run,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
