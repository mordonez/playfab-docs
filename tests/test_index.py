from types import SimpleNamespace

from playfab_docs.content import document_from_crawl_result, write_document
from playfab_docs.index import build_search_index, read_jsonl
from playfab_docs.models import DiscoveredDocument, SourceType


def test_index_contains_retrieval_dimensions(tmp_path):
    discovered = DiscoveredDocument(
        url="https://learn.microsoft.com/en-us/rest/api/playfab/admin/content/get-content-list?view=playfab-rest",
        source_type=SourceType.REST_API,
        toc_path=("Admin", "Content", "Get Content List"),
        api_surface="admin",
    )
    result = SimpleNamespace(
        success=True,
        markdown=SimpleNamespace(
            raw_markdown=(
                "# Get Content List\n\n## Request Body\n\n"
                "The Prefix field limits results to content keys beginning with the supplied value. "
                "The operation returns content metadata and aggregate size information for the title."
            )
        ),
        html='<meta property="og:title" content="Get Content List - PlayFab">',
        links={"internal": [], "external": []},
    )
    write_document(tmp_path / "raw", document_from_crawl_result(discovered, result))

    entries, anomalies = build_search_index(tmp_path / "raw", tmp_path / "reports")

    assert entries[0]["api_surface"] == "admin"
    assert entries[0]["headings"] == ["Get Content List", "Request Body"]
    assert "published_at" in entries[0]
    assert anomalies == []
    assert read_jsonl(tmp_path / "reports" / "search_index.jsonl") == entries
