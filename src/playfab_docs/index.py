from __future__ import annotations

import json
import re
from pathlib import Path

from .content import parse_frontmatter, utc_now

HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
ERROR_MARKERS = ("An unexpected error occurred", "There was an error processing the request")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    atomic_write(path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def build_search_index(raw_dir: Path, reports_dir: Path) -> tuple[list[dict], list[dict]]:
    entries: list[dict] = []
    anomalies: list[dict] = []
    for path in sorted(raw_dir.glob("*/*/*.md")):
        if "_retired" in path.parts:
            continue
        metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        headings = HEADING_RE.findall(body)[:20]
        entry = {
            "title": metadata.get("title", path.stem),
            "url": metadata.get("url", ""),
            "source_type": metadata.get("source_type", ""),
            "toc_path": metadata.get("toc_path", []),
            "product_area": metadata.get("product_area", ""),
            "api_surface": metadata.get("api_surface", ""),
            "content_status": metadata.get("content_status", "current"),
            "published_at": metadata.get("published_at", ""),
            "updated_at": metadata.get("updated_at", ""),
            "fetched_at": metadata.get("fetched_at", ""),
            "service": metadata.get("service", ""),
            "api_version": metadata.get("api_version", ""),
            "headings": headings,
            "path": str(path.relative_to(raw_dir.parent)),
        }
        entries.append(entry)
        words = len(body.split())
        if words < 15:
            anomalies.append({"kind": "short_body", "url": entry["url"], "path": entry["path"], "words": words})
        if not headings:
            anomalies.append({"kind": "missing_heading", "url": entry["url"], "path": entry["path"]})
        if any(marker in body for marker in ERROR_MARKERS):
            anomalies.append({"kind": "error_marker", "url": entry["url"], "path": entry["path"]})

    entries.sort(key=lambda item: (item["source_type"], item["product_area"], item["api_surface"], item["title"]))
    write_jsonl(reports_dir / "search_index.jsonl", entries)
    write_jsonl(reports_dir / "anomalies.jsonl", anomalies)
    return entries, anomalies


def write_summary(reports_dir: Path, summary: dict) -> None:
    payload = {"generated_at": utc_now(), **summary}
    atomic_write(reports_dir / "summary.json", json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
