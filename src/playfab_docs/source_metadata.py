from __future__ import annotations

import asyncio
import json
import re
import shutil
import urllib.request
from collections.abc import Iterable
from pathlib import Path

from .models import DiscoveredDocument, SourceType

FRONTMATTER_END = re.compile(r"^---\s*$", re.MULTILINE)
METADATA_LINE = re.compile(r"^(ms\.date|updated_at|ms\.service):\s*(.*?)\s*$", re.MULTILINE)


def fetch_source_metadata(url: str, timeout: int = 30) -> dict[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/markdown",
            "User-Agent": "playfab-context-builder/0.1 (+https://github.com/mordonez/playfab-context-builder)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
    if not text.startswith("---"):
        raise ValueError(f"Microsoft Learn returned no Markdown frontmatter: {url}")
    closing = FRONTMATTER_END.search(text, 4)
    if not closing:
        raise ValueError(f"Microsoft Learn returned unterminated Markdown frontmatter: {url}")
    values = {key: value.strip("'\"") for key, value in METADATA_LINE.findall(text[4 : closing.start()])}
    return values


async def fetch_metadata_many(
    documents: Iterable[DiscoveredDocument], concurrency: int = 3
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 3)))
    metadata: dict[str, dict[str, str]] = {}
    failures: dict[str, str] = {}
    ordered = list(documents)
    processed = 0

    async def fetch(document: DiscoveredDocument) -> None:
        nonlocal processed
        async with semaphore:
            try:
                metadata[document.url] = await asyncio.to_thread(fetch_source_metadata, document.url)
            except (OSError, ValueError) as error:
                failures[document.url] = str(error)
            processed += 1
            if processed % 100 == 0 or processed == len(ordered):
                print(
                    f"Fetched metadata {processed}/{len(ordered)} ({len(failures)} failed)",
                    flush=True,
                )

    await asyncio.gather(*(fetch(document) for document in ordered))
    return metadata, failures


async def enrich_library_metadata(raw_dir: Path, concurrency: int = 3) -> tuple[int, dict[str, str]]:
    from .content import parse_frontmatter

    records: list[tuple[Path, DiscoveredDocument, dict, str]] = []
    for path in raw_dir.glob("*/*/*.md"):
        if "_retired" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        values, _body = parse_frontmatter(text)
        if not values.get("url") or not values.get("source_type"):
            continue
        document = DiscoveredDocument(
            url=values["url"],
            source_type=SourceType(values["source_type"]),
            toc_path=tuple(values.get("toc_path", [])),
            product_area=values.get("product_area", "_root"),
            api_surface=values.get("api_surface", "_root"),
        )
        records.append((path, document, values, text))

    metadata, failures = await fetch_metadata_many((record[1] for record in records), concurrency=concurrency)
    changed = 0
    for path, document, values, text in records:
        source = metadata.get(document.url)
        if not source:
            continue
        replacements = {
            "published_at": source.get("ms.date", values.get("published_at", "")),
            "updated_at": source.get("updated_at", values.get("updated_at", "")),
            "service": values.get("service") or source.get("ms.service", ""),
        }
        updated = text
        for key, value in replacements.items():
            updated = re.sub(
                rf"^{re.escape(key)}: .*?$",
                f"{key}: {json.dumps(value, ensure_ascii=False)}",
                updated,
                count=1,
                flags=re.MULTILINE,
            )
        if updated == text:
            continue
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(path)
        changed += 1
    return changed, failures


async def enrich_snapshot_metadata(docs_dir: Path, concurrency: int = 3) -> int:
    from .index import build_search_index
    from .snapshot import create_staging, publish

    staging = create_staging(docs_dir)
    try:
        changed, failures = await enrich_library_metadata(staging.raw, concurrency=concurrency)
        if failures:
            raise RuntimeError(f"Metadata enrichment failed for {len(failures)} documents")
        build_search_index(staging.raw, staging.reports)
        publish(staging.root, docs_dir)
        return changed
    except BaseException:
        if staging.root.exists():
            shutil.rmtree(staging.root)
        raise
