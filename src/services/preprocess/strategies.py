"""Lightweight preprocessing strategy functions.

These functions are provided separately from FetcherService to reduce
class responsibilities and enable reuse and testing.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(raw: str) -> str:
    """Normalize a single URL candidate (add scheme, strip tracking params).

    This mirrors the simple normalization logic used in the service.
    """
    trail = ").,;:]}'\""
    s = raw.strip().rstrip(trail)
    if not s.lower().startswith(("http://", "https://")):
        # Force https for consistency
        if s.lower().startswith("t.me/"):
            s = "https://" + s
        else:
            s = "https://" + s
    p = urlparse(s)
    domain = p.netloc.lower()
    path = p.path if p.path != "/" else "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    q = parse_qs(p.query, keep_blank_values=True)
    tracking = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "ref",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }
    q = {k: v for k, v in q.items() if k not in tracking}
    new_query = urlencode(q, doseq=True)
    return urlunparse((p.scheme, domain, path, "", new_query, p.fragment))


def estimate_tokens(text: str) -> int:
    """Very rough token estimate based on word count.

    Approximately 1.3 tokens per word.
    """
    if not text:
        return 0
    words = len(text.split())
    return int(round(words * 1.3))


def classify_message(text: str, message: Any, source_info: Any) -> str:
    """Heuristic message classification.

    Returns one of: question|answer|code|log|spam|service|other.
    """
    is_service = getattr(message, "action", None) is not None
    if not text:
        return "service" if is_service else "other"
    lowered = text.lower()
    # Question
    if (
        "?" in text
        and any(
            lowered.startswith(prefix)
            for prefix in (
                "как ",
                "почему ",
                "что ",
                "где ",
                "когда ",
                "можно ли",
                "how ",
                "why ",
                "what ",
                "where ",
                "when ",
                "can i",
            )
        )
        and len(text) > 15
    ):
        return "question"
    # Code
    code_markers = [
        "```",
        "def ",
        "class ",
        "import ",
        "for ",
        "if ",
        "else:",
        "try:",
    ]
    code_like = (
        len(text) > 40
        and sum(c.isdigit() for c in text) > 5
        and "(" in text
        and ":" in text
    )
    if any(m in text for m in code_markers) or code_like:
        return "code"
    # Log / stacktrace
    log_markers = [
        "traceback",
        "error",
        "exception",
        "warn",
        "INFO",
        "DEBUG",
    ]
    if any(m in lowered for m in log_markers):
        return "log"
    # Service
    if is_service:
        return "service"
    # Spam (simplistic)
    spam_tokens = [
        "free",
        "зарегистрируйся",
        "подпишись",
        "скидка",
        "earn",
        "promo",
    ]
    link_count = text.count("http://") + text.count("https://") + text.count("t.me/")
    if link_count >= 3 or any(tok in lowered for tok in spam_tokens):
        return "spam"
    # Answer
    if (
        lowered.startswith(">")
        or lowered.startswith("ответ")
        or lowered.startswith("re:")
    ):
        return "answer"
    return "other"


def detect_language(text: str) -> str:
    """Lightweight language detection (ru|en|other) by character set proportion."""
    if not text:
        return "other"
    cyr = sum(1 for c in text if "а" <= c.lower() <= "я")
    lat = sum(1 for c in text if "a" <= c.lower() <= "z")
    total_alpha = cyr + lat
    if total_alpha < 5:
        return "other"
    if cyr / max(total_alpha, 1) >= 0.6:
        return "ru"
    if lat / max(total_alpha, 1) >= 0.6:
        return "en"
    return "other"
