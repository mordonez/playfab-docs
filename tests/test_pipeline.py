import asyncio
from types import SimpleNamespace

from playfab_docs import pipeline
from playfab_docs.content import document_from_crawl_result
from playfab_docs.index import read_jsonl, write_jsonl
from playfab_docs.manifests import GUIDES, REST_API, parse_manifest


def test_build_publishes_both_source_families(monkeypatch, tmp_path):
    guide_manifest = {"items": [{"toc_title": "Multiplayer", "href": "multiplayer/lobby"}]}
    rest_manifest = {"items": [{"toc_title": "Admin", "href": "admin/content/get-content-list"}]}

    documents = parse_manifest(GUIDES, guide_manifest) + parse_manifest(REST_API, rest_manifest)

    def fake_discovery():
        return documents, [(GUIDES, guide_manifest), (REST_API, rest_manifest)]

    async def fake_crawl(documents, **_kwargs):
        for discovered in documents:
            result = SimpleNamespace(
                success=True,
                markdown=SimpleNamespace(
                    raw_markdown=(
                        f"# {discovered.toc_path[-1]}\n\n"
                        "This fixture contains enough source-backed documentation words to pass the anomaly threshold cleanly. "
                        "It verifies that the complete pipeline publishes both source families into one atomic snapshot."
                    )
                ),
                html=f'<meta property="og:title" content="{discovered.toc_path[-1]} - PlayFab">',
                links={"internal": [], "external": []},
            )
            yield document_from_crawl_result(discovered, result)

    monkeypatch.setattr(pipeline, "discover_all_live", fake_discovery)
    monkeypatch.setattr(pipeline, "crawl_documents", fake_crawl)
    docs_dir = tmp_path / "library"
    stale = docs_dir / "raw" / "official-guide" / "old-taxonomy" / "multiplayer--lobby.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale duplicate", encoding="utf-8")
    write_jsonl(
        docs_dir / "reports" / "search_index.jsonl",
        [{"url": documents[0].url, "path": str(stale.relative_to(docs_dir))}],
    )

    summary = asyncio.run(pipeline.build(docs_dir=docs_dir))
    entries = read_jsonl(docs_dir / "reports" / "search_index.jsonl")

    assert summary["status"] == "success"
    assert summary["indexed_total"] == 2
    assert {entry["source_type"] for entry in entries} == {"official-guide", "rest-api"}
    assert len(list((docs_dir / "raw").glob("*/*/*.md"))) == 2
    assert not list(tmp_path.glob(".library.staging-*"))
