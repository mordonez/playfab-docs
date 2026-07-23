from playfab_docs.manifests import GUIDES, REST_API, iter_toc_entries, nested_guide_families, parse_manifest
from playfab_docs.models import SourceType


def test_iter_toc_entries_preserves_full_hierarchy():
    payload = [
        {
            "toc_title": "Multiplayer",
            "children": [{"toc_title": "Lobby", "href": "multiplayer/lobby/"}],
        }
    ]

    assert list(iter_toc_entries(payload)) == [("multiplayer/lobby/", ("Multiplayer", "Lobby"))]


def test_parse_guide_manifest_classifies_product_area_and_canonicalizes_locale():
    payload = {
        "items": [
            {
                "toc_title": "Multiplayer",
                "children": [{"toc_title": "Lobby", "href": "/es-es/xbox/playfab/multiplayer/lobby/"}],
            }
        ]
    }

    documents = parse_manifest(GUIDES, payload)

    assert documents[0].url == "https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/lobby"
    assert documents[0].product_area == "multiplayer"
    assert documents[0].source_type is SourceType.OFFICIAL_GUIDE


def test_parse_rest_manifest_preserves_view_and_classifies_surface():
    payload = {
        "items": [
            {
                "toc_title": "Admin",
                "children": [{"toc_title": "Get Content List", "href": "admin/content/get-content-list"}],
            }
        ]
    }

    document = parse_manifest(REST_API, payload)[0]

    assert (
        document.url
        == "https://learn.microsoft.com/en-us/rest/api/playfab/admin/content/get-content-list?view=playfab-rest"
    )
    assert document.api_surface == "admin"
    assert document.source_type is SourceType.REST_API


def test_nested_guide_families_are_derived_from_root_service_hubs():
    payload = {
        "items": [
            {"toc_title": "PlayFab Fundamentals", "href": "get-started/"},
            {
                "toc_title": "PlayFab services",
                "children": [
                    {"toc_title": "Identity", "href": "identity/"},
                    {"toc_title": "Multiplayer", "href": "multiplayer/"},
                ],
            },
        ]
    }

    families = nested_guide_families(payload)

    assert [(family.product_area, family.manifest_url) for family in families] == [
        ("fundamentals", "https://learn.microsoft.com/en-us/xbox/playfab/get-started/toc.json"),
        ("identity", "https://learn.microsoft.com/en-us/xbox/playfab/identity/toc.json"),
        ("multiplayer", "https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/toc.json"),
    ]
