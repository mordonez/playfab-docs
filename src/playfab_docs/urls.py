from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import PurePosixPath
from urllib.parse import urlencode, urlsplit, urlunsplit

from .models import DiscoveredDocument, SourceType

LOCALE_RE = re.compile(r"^/[a-z]{2}(?:-[a-z]{2})?/")
SAFE_SEGMENT_RE = re.compile(r"[^a-z0-9]+")


def slug_segment(value: str) -> str:
    if value == "_root":
        return value
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return SAFE_SEGMENT_RE.sub("-", normalized).strip("-") or "_root"


def canonicalize_url(url: str, source_type: SourceType) -> str | None:
    split = urlsplit(url)
    if split.netloc.lower() != "learn.microsoft.com":
        return None
    path = LOCALE_RE.sub("/en-us/", split.path)
    path = re.sub(r"/{2,}", "/", path)

    if source_type is SourceType.OFFICIAL_GUIDE:
        if not path.startswith("/en-us/xbox/playfab"):
            return None
        query = ""
    else:
        if not path.startswith("/en-us/rest/api/playfab"):
            return None
        query = urlencode({"view": "playfab-rest"})

    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunsplit(("https", "learn.microsoft.com", path, query, ""))


def document_relative_path(document: DiscoveredDocument) -> PurePosixPath:
    split = urlsplit(document.url)
    if document.source_type is SourceType.OFFICIAL_GUIDE:
        prefix = "/en-us/xbox/playfab/"
        bucket = document.product_area
    else:
        prefix = "/en-us/rest/api/playfab/"
        bucket = document.api_surface
    remainder = split.path.removeprefix(prefix).strip("/") or "index"
    parts = [slug_segment(part) for part in remainder.split("/")]
    stem = "--".join(parts)
    if len(stem) > 180:
        digest = hashlib.sha256(document.url.encode()).hexdigest()[:10]
        stem = f"{stem[:160].rstrip('-')}--{digest}"
    return PurePosixPath(document.source_type.value, bucket, f"{stem}.md")
