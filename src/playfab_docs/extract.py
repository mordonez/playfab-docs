from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from .content import document_from_crawl_result
from .models import DiscoveredDocument, ExtractedDocument, ExtractionFailure
from .source_metadata import fetch_metadata_many
from .urls import canonicalize_url

CONTENT_SELECTOR = "[data-main-column]"
EXCLUDED_SELECTOR = ", ".join(
    (
        "#article-header",
        "#article-metadata",
        "[unauthorized-private-section]",
        "[data-id='ai-summary']",
        "#center-doc-outline",
        "#ms--inline-notifications",
        "#site-user-feedback-footer",
        "#assertive-live-region",
        "#polite-live-region",
    )
)


def crawler_config(*, use_cache: bool = False, concurrency: int = 3) -> CrawlerRunConfig:
    return CrawlerRunConfig(
        css_selector=CONTENT_SELECTOR,
        excluded_selector=EXCLUDED_SELECTOR,
        wait_for=f"css:{CONTENT_SELECTOR}",
        page_timeout=60_000,
        semaphore_count=max(1, min(concurrency, 3)),
        max_retries=2,
        mean_delay=0.25,
        max_range=0.75,
        cache_mode=CacheMode.ENABLED if use_cache else CacheMode.BYPASS,
        stream=True,
        verbose=False,
    )


async def crawl_documents(
    documents: Iterable[DiscoveredDocument], *, use_cache: bool = False, concurrency: int = 3
) -> AsyncIterator[ExtractedDocument | ExtractionFailure]:
    ordered = list(documents)
    by_url = {document.url: document for document in ordered}
    source_metadata, metadata_failures = await fetch_metadata_many(ordered, concurrency=concurrency)
    browser = BrowserConfig(
        headless=True, user_agent="playfab-context-builder/0.1 (+https://github.com/mordonez/playfab-context-builder)"
    )
    async with AsyncWebCrawler(config=browser) as crawler:
        results = await crawler.arun_many(
            urls=[document.url for document in ordered],
            config=crawler_config(use_cache=use_cache, concurrency=concurrency),
        )
        async for result in results:
            discovered = by_url.get(result.url) or by_url.get(result.url.rstrip("/"))
            if discovered is None:
                for candidate_type in (ordered[0].source_type, *[item.source_type for item in ordered]):
                    canonical = canonicalize_url(result.url, candidate_type)
                    if canonical and canonical in by_url:
                        discovered = by_url[canonical]
                        break
            if discovered is None:
                yield ExtractionFailure(ordered[0], f"crawler returned unexpected URL: {result.url}")
                continue
            if discovered.url in metadata_failures:
                yield ExtractionFailure(discovered, f"metadata fetch failed: {metadata_failures[discovered.url]}")
                continue
            try:
                yield document_from_crawl_result(discovered, result, source_metadata.get(discovered.url))
            except ValueError as error:
                yield ExtractionFailure(discovered, str(error))
