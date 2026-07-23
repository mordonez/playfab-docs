from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from .content import write_document
from .extract import crawl_documents
from .index import atomic_write, build_search_index, write_jsonl, write_summary
from .manifests import discover_all_live
from .models import DiscoveredDocument, ExtractedDocument, ExtractionFailure, SourceType
from .snapshot import create_staging, previous_entries, publish, retire_removed


def resolve_docs_dir() -> Path:
    override = os.environ.get("PLAYFAB_DOCS_DIR")
    return Path(override).expanduser() if override else Path.home() / ".playfab-docs"


def filter_documents(
    documents: list[DiscoveredDocument], source_type: str | None, area: str | None, surface: str | None
) -> list[DiscoveredDocument]:
    selected = documents
    if source_type:
        selected = [item for item in selected if item.source_type.value == source_type]
    if area:
        selected = [item for item in selected if item.product_area == area]
    if surface:
        selected = [item for item in selected if item.api_surface == surface]
    return selected


def write_discovery_reports(staging, manifests: list[tuple], documents: list[DiscoveredDocument]) -> None:
    manifest_dir = staging.reports / "manifests"
    if manifest_dir.exists():
        shutil.rmtree(manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for family, payload in manifests:
        suffix = family.product_area or "root"
        atomic_write(
            manifest_dir / f"{family.source_type.value}--{suffix}.json",
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        )
    for source_type in SourceType:
        urls = sorted(item.url for item in documents if item.source_type is source_type)
        atomic_write(staging.reports / f"{source_type.value}_urls.txt", "\n".join(urls) + ("\n" if urls else ""))


async def build(
    *,
    docs_dir: Path,
    max_pages: int | None = None,
    source_type: str | None = None,
    area: str | None = None,
    surface: str | None = None,
    concurrency: int = 3,
    use_cache: bool = False,
) -> dict:
    all_documents, manifests = discover_all_live()
    selected = filter_documents(all_documents, source_type, area, surface)
    if max_pages is not None:
        selected = selected[:max_pages]
    if not selected:
        raise RuntimeError("No documents match the requested filters")

    full_refresh = max_pages is None and source_type is None and area is None and surface is None
    previous = previous_entries(docs_dir)
    staging = create_staging(docs_dir)
    failures: list[dict] = []
    successful: list[ExtractedDocument] = []

    try:
        current_urls = {item.url for item in all_documents}
        manifest_changes = retire_removed(staging, previous, current_urls) if full_refresh else []
        if full_refresh:
            for source in SourceType:
                active_source = staging.raw / source.value
                if active_source.exists():
                    shutil.rmtree(active_source)
        write_discovery_reports(staging, manifests, all_documents)
        processed = 0
        async for outcome in crawl_documents(selected, use_cache=use_cache, concurrency=concurrency):
            processed += 1
            if isinstance(outcome, ExtractionFailure):
                previous_copy = previous.get(outcome.discovered.url)
                if previous_copy and full_refresh:
                    relative = Path(previous_copy["path"])
                    old_path = docs_dir / relative
                    preserved_path = staging.root / relative
                    if old_path.exists():
                        preserved_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(old_path, preserved_path)
                failures.append(
                    {
                        "url": outcome.discovered.url,
                        "reason": outcome.reason,
                        "preserved_previous": bool(previous_copy),
                    }
                )
            else:
                write_document(staging.raw, outcome)
                successful.append(outcome)
            if processed % 50 == 0 or processed == len(selected):
                print(
                    f"Processed {processed}/{len(selected)} documents "
                    f"({len(successful)} extracted, {len(failures)} failed)",
                    flush=True,
                )

        new_urls = sorted(current_urls - set(previous)) if full_refresh else []
        manifest_changes.extend({"kind": "manifest_added", "url": url} for url in new_urls)

        known_urls = current_urls
        internal_links = {link for document in successful for link in document.internal_links}
        coverage_gaps = [{"url": url, "kind": "absent_from_manifest"} for url in sorted(internal_links - known_urls)]
        external = sorted({link for document in successful for link in document.external_references})
        write_jsonl(staging.reports / "coverage_gaps.jsonl", coverage_gaps)
        write_jsonl(staging.reports / "external_references.jsonl", [{"url": url} for url in external])
        write_jsonl(staging.reports / "manifest_changes.jsonl", manifest_changes)
        write_jsonl(staging.reports / "fetch_failures.jsonl", failures)

        entries, anomalies = build_search_index(staging.raw, staging.reports)
        by_source = Counter(entry["source_type"] for entry in entries)
        summary = {
            "status": "failed" if any(not failure["preserved_previous"] for failure in failures) else "success",
            "manifest_total": len(all_documents),
            "selected_total": len(selected),
            "extracted_total": len(successful),
            "indexed_total": len(entries),
            "by_source": dict(sorted(by_source.items())),
            "fetch_failures": len(failures),
            "unresolved_failures": sum(not item["preserved_previous"] for item in failures),
            "anomalies": len(anomalies),
            "coverage_gaps": len(coverage_gaps),
            "external_references": len(external),
            "manifest_changes": len(manifest_changes),
            "full_refresh": full_refresh,
        }
        write_summary(staging.reports, summary)

        if summary["unresolved_failures"]:
            raise RuntimeError(f"Build has {summary['unresolved_failures']} hard failures without a previous copy")
        publish(staging.root, docs_dir)
        return summary
    except BaseException:
        if staging.root.exists():
            shutil.rmtree(staging.root)
        raise


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description="Build a local PlayFab documentation library.")
    argument_parser.add_argument("--max-pages", type=int, help="Limit extraction for a smoke test.")
    argument_parser.add_argument("--source-type", choices=[item.value for item in SourceType])
    argument_parser.add_argument("--area", help="Filter by normalized Product Area slug.")
    argument_parser.add_argument("--surface", help="Filter by normalized API Surface slug.")
    argument_parser.add_argument("--concurrency", type=int, default=3, choices=range(1, 4))
    argument_parser.add_argument(
        "--use-cache", action="store_true", help="Use Crawl4AI's cache (recommended for tests)."
    )
    return argument_parser


def main() -> None:
    args = parser().parse_args()
    try:
        summary = asyncio.run(
            build(
                docs_dir=resolve_docs_dir(),
                max_pages=args.max_pages,
                source_type=args.source_type,
                area=args.area,
                surface=args.surface,
                concurrency=args.concurrency,
                use_cache=args.use_cache,
            )
        )
    except (RuntimeError, OSError, ValueError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
