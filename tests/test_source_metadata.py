import asyncio
from io import BytesIO

from playfab_docs import source_metadata
from playfab_docs.content import document_from_crawl_result, parse_frontmatter, write_document
from playfab_docs.models import DiscoveredDocument, SourceType


class FakeResponse:
    status = 200

    def __init__(self, body: str):
        self.body = BytesIO(body.encode())

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body.read()


def test_fetch_source_metadata_reads_microsoft_markdown_frontmatter(monkeypatch):
    body = (
        "---\nms.date: 2025-04-08T00:00:00Z\nupdated_at: 2026-03-10T22:13:00Z\nms.service: azure-playfab\n---\n# Lobby"
    )
    monkeypatch.setattr(source_metadata.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse(body))

    values = source_metadata.fetch_source_metadata("https://learn.microsoft.com/en-us/xbox/playfab/test")

    assert values == {
        "ms.date": "2025-04-08T00:00:00Z",
        "updated_at": "2026-03-10T22:13:00Z",
        "ms.service": "azure-playfab",
    }


def test_enrich_library_metadata_updates_existing_frontmatter(monkeypatch, tmp_path):
    discovered = DiscoveredDocument(
        url="https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/lobby",
        source_type=SourceType.OFFICIAL_GUIDE,
        toc_path=("Multiplayer", "Lobby"),
        product_area="multiplayer",
    )
    result = type(
        "Result",
        (),
        {
            "success": True,
            "markdown": type("Markdown", (), {"raw_markdown": "# Lobby\n\nUseful content for players."})(),
            "html": "",
            "links": {"internal": [], "external": []},
        },
    )()
    path = write_document(tmp_path, document_from_crawl_result(discovered, result))

    async def fake_many(_documents, concurrency=3):
        return {
            discovered.url: {
                "ms.date": "2025-04-08T00:00:00Z",
                "updated_at": "2026-03-10T22:13:00Z",
                "ms.service": "azure-playfab",
            }
        }, {}

    monkeypatch.setattr(source_metadata, "fetch_metadata_many", fake_many)
    changed, failures = asyncio.run(source_metadata.enrich_library_metadata(tmp_path))
    values, _body = parse_frontmatter(path.read_text(encoding="utf-8"))

    assert changed == 1
    assert failures == {}
    assert values["published_at"] == "2025-04-08T00:00:00Z"
    assert values["updated_at"] == "2026-03-10T22:13:00Z"
    assert values["service"] == "azure-playfab"
