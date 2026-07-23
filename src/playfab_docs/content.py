from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .models import ContentStatus, DiscoveredDocument, ExtractedDocument, SourceType
from .urls import canonicalize_url, document_relative_path

STATUS_PATTERNS = (
    (
        ContentStatus.LEGACY,
        re.compile(
            r"^#\s+.*\b(legacy|deprecated)\b|\b(?:this|the)\s+[^.\n]{0,120}\s+"
            r"(?:is|are|has been|have been)\s+(?:now\s+)?(?:deprecated|obsolete|superseded|being replaced)\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        ContentStatus.MAINTENANCE,
        re.compile(
            r"\b(?:this|the)\s+[^.\n]{0,120}\s+(?:is|are)\s+(?:in\s+)?maintenance mode\b",
            re.IGNORECASE,
        ),
    ),
    (
        ContentStatus.PREVIEW,
        re.compile(
            r"^#\s+.*\bpreview\b|\b(?:this|the)\s+[^.\n]{0,120}\s+"
            r"(?:is|are)\s+(?:currently\s+)?(?:in\s+)?(?:public\s+|private\s+|limited\s+)?preview\b",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
)
AUTH_MARKERS = ("access to this page requires authorization", "permission-content-unauthorized-private")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_content_status(markdown: str, context: tuple[str, ...] = ()) -> ContentStatus:
    context_text = " ".join(context)
    if re.search(r"\blegacy\b|\bdeprecated\b", context_text, re.IGNORECASE):
        return ContentStatus.LEGACY
    if re.search(r"\bpreview\b", context_text, re.IGNORECASE):
        return ContentStatus.PREVIEW
    # Lifecycle labels describe the page itself near its title/opening notice.
    # Restricting the signal prevents a current comparison guide from becoming
    # "legacy" merely because it discusses a legacy product later on.
    page_context = markdown[:2_500]
    for status, pattern in STATUS_PATTERNS:
        if pattern.search(page_context):
            return status
    return ContentStatus.CURRENT


def metadata_from_html(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    metadata: dict[str, str] = {}
    for element in soup.select("meta[name][content], meta[property][content]"):
        key = element.get("name") or element.get("property")
        if key:
            metadata[str(key)] = str(element.get("content", "")).strip()

    for entry in soup.select(".metadata dl"):
        term = entry.find("dt")
        definition = entry.find("dd")
        if term and definition:
            metadata[term.get_text(" ", strip=True).rstrip(":").lower().replace(" ", "_")] = definition.get_text(
                " ", strip=True
            )
    return metadata


def normalize_result_links(result, source_type: SourceType) -> tuple[list[str], list[str]]:
    internal: set[str] = set()
    external: set[str] = set()
    links = getattr(result, "links", {}) or {}
    for group in ("internal", "external"):
        for item in links.get(group, []) or []:
            href = item.get("href") if isinstance(item, dict) else str(item)
            if not href:
                continue
            canonical = canonicalize_url(href, source_type)
            if canonical is None:
                other_type = (
                    SourceType.REST_API if source_type is SourceType.OFFICIAL_GUIDE else SourceType.OFFICIAL_GUIDE
                )
                canonical = canonicalize_url(href, other_type)
            if canonical:
                internal.add(canonical)
            elif urlsplit(href).scheme in {"http", "https"}:
                external.add(href.split("#", 1)[0])
    return sorted(internal), sorted(external)


def document_from_crawl_result(
    discovered: DiscoveredDocument, result, source_metadata: dict[str, str] | None = None
) -> ExtractedDocument:
    if not getattr(result, "success", False):
        message = getattr(result, "error_message", "crawl failed") or "crawl failed"
        raise ValueError(message)

    markdown_value = getattr(result, "markdown", None)
    markdown = getattr(markdown_value, "raw_markdown", None) or (
        markdown_value if isinstance(markdown_value, str) else ""
    )
    markdown = markdown.strip()
    if not markdown:
        raise ValueError("empty extracted content")
    lowered = markdown.lower()
    if any(marker in lowered for marker in AUTH_MARKERS):
        raise ValueError("authorization page returned instead of public content")

    html = getattr(result, "html", "") or ""
    metadata = metadata_from_html(html)
    metadata.update(source_metadata or {})
    title = metadata.get("og:title", "").removesuffix(" - PlayFab").strip()
    if not title:
        match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        title = match.group(1).strip() if match else discovered.toc_path[-1]

    internal_links, external_references = normalize_result_links(result, discovered.source_type)
    return ExtractedDocument(
        discovered=discovered,
        title=title,
        markdown=markdown + "\n",
        fetched_at=utc_now(),
        updated_at=metadata.get("updated_at", ""),
        published_at=metadata.get("ms.date", ""),
        content_status=detect_content_status(markdown, (*discovered.toc_path, title)),
        service=metadata.get("service", metadata.get("ms.service", "")),
        api_version=metadata.get("api_version", ""),
        external_references=external_references,
        internal_links=internal_links,
    )


def frontmatter(document: ExtractedDocument) -> str:
    discovered = document.discovered
    values = {
        "url": discovered.url,
        "title": document.title,
        "source_type": discovered.source_type.value,
        "toc_path": list(discovered.toc_path),
        "product_area": discovered.product_area,
        "api_surface": discovered.api_surface,
        "content_status": document.content_status.value,
        "published_at": document.published_at,
        "updated_at": document.updated_at,
        "fetched_at": document.fetched_at,
        "service": document.service,
        "api_version": document.api_version,
        "internal_links": document.internal_links,
        "external_references": document.external_references,
        "content_hash": f"sha256:{hashlib.sha256(document.markdown.encode()).hexdigest()}",
    }
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in values.items()), "---", ""]
    return "\n".join(lines)


def write_document(raw_dir: Path, document: ExtractedDocument) -> Path:
    relative = Path(document_relative_path(document.discovered))
    path = raw_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(frontmatter(document) + document.markdown, encoding="utf-8")
    temporary.replace(path)
    return path


def parse_frontmatter(markdown: str) -> tuple[dict, str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    end = markdown.find("\n---\n", 4)
    if end < 0:
        return {}, markdown
    values: dict = {}
    for line in markdown[4:end].splitlines():
        key, separator, raw = line.partition(":")
        if not separator:
            continue
        try:
            values[key] = json.loads(raw.strip())
        except json.JSONDecodeError:
            values[key] = raw.strip()
    return values, markdown[end + 5 :]


def reclassify_library(raw_dir: Path) -> int:
    changed = 0
    for path in raw_dir.glob("*/*/*.md"):
        if "_retired" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(text)
        context = (*metadata.get("toc_path", []), metadata.get("title", ""))
        status = detect_content_status(body, context).value
        if metadata.get("content_status") == status:
            continue
        updated = re.sub(
            r"^content_status: .*?$",
            f"content_status: {json.dumps(status)}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(path)
        changed += 1
    return changed
