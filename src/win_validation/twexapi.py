"""Read X timelines and replies through TWEXAPI's public REST API."""
from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from .http import request

API = "https://api.twexapi.io"


class TwexError(RuntimeError):
    def __init__(self, message: str, record: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.record = record or {}


def _page(path: str, payload: dict[str, Any], token: str, source: str, timeout: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    record, body = request(source, API + path, "social_twexapi", token=token, method="POST", payload=payload, timeout=timeout)
    if record.get("http_status") != 200 or record.get("result_status") != "SUCCESS_WITH_EVIDENCE":
        raise TwexError("TWEXAPI request failed", record)
    try:
        response = json.loads(body)
        if not isinstance(response, dict):
            raise ValueError("unexpected TWEXAPI response")
        if response.get("code") != 200:
            record["api_code"] = response.get("code")
            raise TwexError("TWEXAPI rejected the request", record)
        if not isinstance(response.get("data"), list) or not isinstance(response.get("has_next_page"), bool):
            raise ValueError("unexpected TWEXAPI response")
        items = response["data"]
        if any(not isinstance(item, dict) for item in items):
            raise ValueError("unexpected TWEXAPI item")
        record["has_next_page"] = response["has_next_page"]
        return items, record
    except (ValueError, TypeError, AttributeError) as exc:
        raise TwexError("TWEXAPI returned an invalid response", record) from exc


def _normalise(item: dict[str, Any], *, default_author: str = "", parent_url: str = "") -> dict[str, Any] | None:
    tweet_id = str(item.get("tweet_id") or "").strip()
    if not re.fullmatch(r"\d{1,30}", tweet_id):
        return None
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    author = str(item.get("author_screen_name") or user.get("screen_name") or default_author).lstrip("@")
    if author and not re.fullmatch(r"[A-Za-z0-9_]{1,15}", author):
        author = ""
    url = f"https://x.com/{author or 'i'}/status/{tweet_id}"
    return {
        "tweetId": tweet_id,
        "text": item.get("full_text") or item.get("text") or "",
        "createdAt": item.get("created_at_datetime") or item.get("created_at") or "",
        "url": url,
        "username": author,
        "postUrl": parent_url,
    }


def timeline(handle: str, token: str, *, max_posts: int, timeout: int = 30) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
        raise TwexError("invalid X account name")
    path = "/twitter/" + urllib.parse.quote(handle, safe="") + "/timeline/page"
    items, record = _page(path, {"count": min(max_posts, 100)}, token, "social_twexapi_timeline_" + handle.casefold(), timeout)
    posts = []
    for item in items:
        post = _normalise(item, default_author=handle)
        if post and post["username"].casefold() == handle.casefold():
            posts.append(post)
        if len(posts) >= max_posts:
            break
    return posts, record


def replies(tweet_id: str, parent_url: str, token: str, *, max_replies: int, timeout: int = 30) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not re.fullmatch(r"\d{1,30}", tweet_id):
        raise TwexError("invalid tweet ID")
    path = f"/twitter/tweets/{tweet_id}/replies/page"
    items, record = _page(path, {"sort_by": "Recency"}, token, "social_twexapi_replies_" + tweet_id, timeout)
    result = []
    for item in items:
        reply = _normalise(item, parent_url=parent_url)
        if reply:
            result.append(reply)
        if len(result) >= max_replies:
            break
    return result, record
