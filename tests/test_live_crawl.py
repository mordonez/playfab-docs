import asyncio
import os

import pytest

from playfab_docs.extract import crawl_documents
from playfab_docs.models import DiscoveredDocument, ExtractedDocument, SourceType


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("PLAYFAB_RUN_LIVE_TESTS"), reason="set PLAYFAB_RUN_LIVE_TESTS=1")
def test_live_guide_and_rest_extraction():
    documents = [
        DiscoveredDocument(
            url="https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/lobby",
            source_type=SourceType.OFFICIAL_GUIDE,
            toc_path=("Multiplayer", "Lobby"),
            product_area="multiplayer",
        ),
        DiscoveredDocument(
            url=("https://learn.microsoft.com/en-us/rest/api/playfab/admin/content/get-content-list?view=playfab-rest"),
            source_type=SourceType.REST_API,
            toc_path=("Admin", "Content", "Get Content List"),
            api_surface="admin",
        ),
    ]

    async def collect():
        return [outcome async for outcome in crawl_documents(documents, use_cache=True, concurrency=1)]

    outcomes = asyncio.run(collect())

    assert len(outcomes) == 2
    assert all(isinstance(outcome, ExtractedDocument) for outcome in outcomes)
    by_source = {outcome.discovered.source_type: outcome for outcome in outcomes}
    assert "Cross-platform scalable lobby service" in by_source[SourceType.OFFICIAL_GUIDE].markdown
    assert by_source[SourceType.OFFICIAL_GUIDE].updated_at
    assert "Request Body" in by_source[SourceType.REST_API].markdown
    assert by_source[SourceType.REST_API].updated_at
