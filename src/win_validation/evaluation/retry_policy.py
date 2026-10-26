"""Pure decision helpers matching the versioned no-cost retry policy."""

def classify_attempt(http_status: int | None, *, timed_out: bool=False, dns_error: bool=False) -> str:
    if timed_out or dns_error or http_status is None:
        return 'TRANSIENT_ERROR'
    if http_status in (401,403):
        return 'AUTH_BLOCKED'
    if http_status == 429:
        return 'RATE_LIMITED'
    if http_status in (500,502,503,504):
        return 'TRANSIENT_ERROR'
    if 200 <= http_status < 300:
        return 'SUCCESS_WITH_EVIDENCE'
    if 400 <= http_status < 500:
        return 'VALIDATION_ERROR'
    return 'UNAVAILABLE'

def should_retry(*, status: str, attempt: int, max_attempts: int=3,
                 quota_safe: bool=True, retry_after_available: bool=True,
                 query_changed: bool=False) -> bool:
    if not quota_safe or attempt >= max_attempts:
        return False
    if status == 'TRANSIENT_ERROR':
        return True
    if status == 'RATE_LIMITED':
        return retry_after_available
    if status == 'EMPTY_VALID_RESPONSE':
        return query_changed
    return False

def page_complete(next_page: str | None) -> bool:
    return next_page is None
