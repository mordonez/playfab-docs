from types import SimpleNamespace

import pytest

from playfab_docs.content import (
    detect_content_status,
    document_from_crawl_result,
    parse_frontmatter,
    reclassify_library,
    write_document,
)
from playfab_docs.models import ContentStatus, DiscoveredDocument, SourceType


def discovered(source_type=SourceType.OFFICIAL_GUIDE):
    return DiscoveredDocument(
        url="https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/lobby",
        source_type=source_type,
        toc_path=("Multiplayer", "Lobby"),
        product_area="multiplayer",
    )


def result(markdown="# Lobby\n\nUseful content", html=""):
    return SimpleNamespace(
        success=True,
        markdown=SimpleNamespace(raw_markdown=markdown),
        html=html,
        links={"internal": [], "external": []},
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This feature is in public preview.", ContentStatus.PREVIEW),
        ("This API is in maintenance mode.", ContentStatus.MAINTENANCE),
        ("# Legacy SDK\n\nUse the new SDK instead.", ContentStatus.LEGACY),
        ("Use Lobby for player groups.", ContentStatus.CURRENT),
    ],
)
def test_status_requires_explicit_source_language(text, expected):
    assert detect_content_status(text) is expected


def test_status_ignores_a_legacy_mention_far_below_the_page_introduction():
    text = (
        "# Current integration\n\nUse this recommended integration today.\n" + ("current details " * 300) + "legacy SDK"
    )

    assert detect_content_status(text) is ContentStatus.CURRENT


def test_status_uses_toc_context_and_does_not_apply_a_v1_notice_to_a_v2_page():
    v2_page = "# Catalog overview\n\nEconomy v1 APIs are in maintenance mode and receive no new features."

    assert detect_content_status(v2_page, ("Economy v2 and UGC", "Catalog overview")) is ContentStatus.CURRENT
    assert detect_content_status("# Catalogs", ("Legacy economy", "Catalogs")) is ContentStatus.LEGACY


def test_extracts_metadata_and_writes_json_frontmatter(tmp_path):
    html = """
    <html><head><meta property="og:title" content="Lobby - PlayFab">
    <meta name="updated_at" content="2026-03-10T22:13:00Z"></head></html>
    """
    document = document_from_crawl_result(discovered(), result(html=html))
    path = write_document(tmp_path, document)
    metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))

    assert metadata["title"] == "Lobby"
    assert metadata["updated_at"] == "2026-03-10T22:13:00Z"
    assert metadata["toc_path"] == ["Multiplayer", "Lobby"]
    assert body.startswith("# Lobby")


def test_rejects_empty_and_authorization_pages():
    with pytest.raises(ValueError, match="empty"):
        document_from_crawl_result(discovered(), result(markdown=""))
    with pytest.raises(ValueError, match="authorization"):
        document_from_crawl_result(discovered(), result(markdown="Access to this page requires authorization"))


def test_reclassifies_existing_library_from_toc_context(tmp_path):
    document = document_from_crawl_result(discovered(), result(markdown="# Catalogs\n\nUseful current content"))
    document.discovered = DiscoveredDocument(
        url=document.discovered.url,
        source_type=document.discovered.source_type,
        toc_path=("Legacy economy", "Catalogs"),
        product_area=document.discovered.product_area,
    )
    path = write_document(tmp_path, document)

    assert reclassify_library(tmp_path) == 1
    metadata, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert metadata["content_status"] == "legacy"
