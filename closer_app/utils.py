"""Small dependency-free helpers."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.parse import urlparse


def load_dotenv(path: str = ".env") -> None:
    """Load simple KEY=VALUE lines without requiring python-dotenv."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def clean_text(value: object, max_length: Optional[int] = None) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def add_days_iso(start_iso: Optional[str], days: int) -> str:
    if not start_iso:
        start = date.today()
    else:
        start = date.fromisoformat(start_iso[:10])
    return (start + timedelta(days=days)).isoformat()


def normalize_instagram_handle(value: object) -> str:
    text = clean_text(value).lower()
    if not text:
        return ""
    text = text.replace("https://www.instagram.com/", "")
    text = text.replace("https://instagram.com/", "")
    text = text.replace("http://www.instagram.com/", "")
    text = text.replace("http://instagram.com/", "")
    text = text.strip("/").split("/")[0]
    text = text.lstrip("@")
    text = re.sub(r"[^a-z0-9._]", "", text)
    return text.strip("._")


def instagram_url_from_handle(handle: object) -> str:
    normalized = normalize_instagram_handle(handle)
    if not normalized:
        return ""
    return f"https://www.instagram.com/{normalized}/"


def extract_instagram_url(*texts: object) -> str:
    joined = " ".join(clean_text(text) for text in texts if text)
    match = re.search(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._]+/?", joined)
    if match:
        return match.group(0).rstrip("/") + "/"
    handle_match = re.search(r"(?<!\w)@([A-Za-z0-9._]{3,30})", joined)
    if handle_match:
        return instagram_url_from_handle(handle_match.group(1))
    return ""


def extract_domain(url: object) -> str:
    text = clean_text(url).lower()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = parsed.netloc or parsed.path
    if host.startswith("www."):
        host = host[4:]
    return host.split("/")[0]


def is_placeholder_url(url: object) -> bool:
    text = clean_text(url).lower()
    if not text:
        return False
    host = extract_domain(text)
    if not host:
        return False
    reserved_hosts = {"example.com", "example.org", "example.net"}
    reserved_suffixes = (".example", ".invalid", ".test")
    return host in reserved_hosts or host.startswith("example-") or host.endswith(reserved_suffixes)


def extract_email(*texts: object) -> str:
    joined = " ".join(clean_text(text) for text in texts if text)
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", joined)
    return match.group(0) if match else ""


def first_non_empty(*values: object) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def compact_join(values: Iterable[object], separator: str = " | ") -> str:
    seen = []
    for value in values:
        text = clean_text(value)
        if text and text not in seen:
            seen.append(text)
    return separator.join(seen)


def coerce_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def env_or_setting(settings: Dict[str, str], key: str, env_key: Optional[str] = None) -> str:
    env_name = env_key or key.upper()
    return os.environ.get(env_name) or settings.get(key, "")
