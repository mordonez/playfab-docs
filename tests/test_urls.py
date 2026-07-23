from playfab_docs.models import DiscoveredDocument, SourceType
from playfab_docs.urls import canonicalize_url, document_relative_path


def test_canonicalize_rejects_other_domains_and_cross_family_paths():
    assert canonicalize_url("https://example.com/en-us/xbox/playfab", SourceType.OFFICIAL_GUIDE) is None
    assert (
        canonicalize_url("https://learn.microsoft.com/en-us/rest/api/playfab/admin", SourceType.OFFICIAL_GUIDE) is None
    )


def test_rest_query_is_stable_and_forces_moniker():
    url = "https://learn.microsoft.com/es-es/rest/api/playfab/client/?z=2&view=wrong&a=1#top"

    assert canonicalize_url(url, SourceType.REST_API) == (
        "https://learn.microsoft.com/en-us/rest/api/playfab/client?view=playfab-rest"
    )


def test_document_path_uses_source_and_taxonomy():
    document = DiscoveredDocument(
        url="https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/lobby",
        source_type=SourceType.OFFICIAL_GUIDE,
        toc_path=("Multiplayer", "Lobby"),
        product_area="multiplayer",
    )

    assert str(document_relative_path(document)) == "official-guide/multiplayer/multiplayer--lobby.md"
