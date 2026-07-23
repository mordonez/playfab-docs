from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit

from .models import DiscoveredDocument, SourceFamily, SourceType
from .urls import canonicalize_url, slug_segment

GUIDES = SourceFamily(
    source_type=SourceType.OFFICIAL_GUIDE,
    manifest_url="https://learn.microsoft.com/en-us/xbox/playfab/toc.json",
    base_url="https://learn.microsoft.com/en-us/xbox/playfab/",
)
REST_API = SourceFamily(
    source_type=SourceType.REST_API,
    manifest_url="https://learn.microsoft.com/en-us/rest/api/playfab/toc.json?view=playfab-rest",
    base_url="https://learn.microsoft.com/en-us/rest/api/playfab/",
)
SOURCE_FAMILIES = (GUIDES, REST_API)


def fetch_manifest(family: SourceFamily, timeout: int = 30) -> dict:
    request = urllib.request.Request(family.manifest_url, headers={"User-Agent": "playfab-context-builder/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Manifest returned HTTP {response.status}: {family.manifest_url}")
        data = json.load(response)
    if not isinstance(data.get("items"), list) or not data["items"]:
        raise ValueError(f"Manifest has no items: {family.manifest_url}")
    return data


def nested_guide_families(root_payload: dict) -> list[SourceFamily]:
    candidates: list[tuple[str, str]] = []
    for item in root_payload.get("items", []):
        title = str(item.get("toc_title") or "")
        href = item.get("href")
        if isinstance(href, str) and href not in {"./", "../"} and href.endswith("/"):
            candidates.append((title, href))
        if title == "PlayFab services":
            for child in item.get("children", []):
                child_href = child.get("href")
                if isinstance(child_href, str) and child_href.endswith("/"):
                    candidates.append((str(child.get("toc_title") or ""), child_href))

    families: dict[str, SourceFamily] = {}
    for title, href in candidates:
        base_url = urljoin(GUIDES.base_url, href)
        manifest_url = urljoin(base_url, "toc.json")
        area = "fundamentals" if title == "PlayFab Fundamentals" else slug_segment(title)
        families[manifest_url] = SourceFamily(
            source_type=SourceType.OFFICIAL_GUIDE,
            manifest_url=manifest_url,
            base_url=base_url,
            product_area=area,
        )
    return sorted(families.values(), key=lambda family: family.manifest_url)


def fetch_available_nested_manifests(root_payload: dict) -> list[tuple[SourceFamily, dict]]:
    found: list[tuple[SourceFamily, dict]] = []
    for family in nested_guide_families(root_payload):
        try:
            found.append((family, fetch_manifest(family)))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    return found


def iter_toc_entries(items: Iterable[dict], parents: tuple[str, ...] = ()) -> Iterable[tuple[str, tuple[str, ...]]]:
    for item in items:
        title = str(item.get("toc_title") or item.get("name") or "").strip()
        path = (*parents, title) if title else parents
        href = item.get("href")
        if isinstance(href, str) and href.strip():
            yield href.strip(), path
        children = item.get("children")
        if isinstance(children, list):
            yield from iter_toc_entries(children, path)


def classify_hierarchy(family: SourceFamily, toc_path: tuple[str, ...], url: str) -> tuple[str, str]:
    meaningful = [
        segment for segment in toc_path if segment and segment.lower() not in {"playfab", "playfab rest api reference"}
    ]
    if family.source_type is SourceType.OFFICIAL_GUIDE:
        if family.product_area:
            return family.product_area, "_root"
        area = meaningful[0] if meaningful else "_root"
        return slug_segment(area), "_root"

    relative = urlsplit(url).path.removeprefix(urlsplit(family.base_url).path).split("/", 1)[0]
    surface = relative or (meaningful[0] if meaningful else "_root")
    return "_root", slug_segment(surface)


def parse_manifest(family: SourceFamily, payload: dict) -> list[DiscoveredDocument]:
    documents: dict[str, DiscoveredDocument] = {}
    for href, toc_path in iter_toc_entries(payload.get("items", [])):
        absolute = urljoin(family.base_url, href)
        canonical = canonicalize_url(absolute, family.source_type)
        if canonical is None:
            continue
        product_area, api_surface = classify_hierarchy(family, toc_path, canonical)
        documents[canonical] = DiscoveredDocument(
            url=canonical,
            source_type=family.source_type,
            toc_path=toc_path,
            product_area=product_area,
            api_surface=api_surface,
        )
    if not documents:
        raise ValueError(f"Manifest produced no in-scope documents: {family.manifest_url}")
    return sorted(documents.values(), key=lambda item: item.url)


def discover_all(payloads: dict[SourceType, dict] | None = None) -> list[DiscoveredDocument]:
    documents: list[DiscoveredDocument] = []
    for family in SOURCE_FAMILIES:
        payload = payloads[family.source_type] if payloads else fetch_manifest(family)
        documents.extend(parse_manifest(family, payload))
    return documents


def discover_all_live() -> tuple[list[DiscoveredDocument], list[tuple[SourceFamily, dict]]]:
    root_payload = fetch_manifest(GUIDES)
    manifest_pairs = [(GUIDES, root_payload), (REST_API, fetch_manifest(REST_API))]
    manifest_pairs.extend(fetch_available_nested_manifests(root_payload))

    documents: dict[str, DiscoveredDocument] = {}
    for family, payload in manifest_pairs:
        for document in parse_manifest(family, payload):
            documents[document.url] = document
    return sorted(documents.values(), key=lambda item: item.url), manifest_pairs
