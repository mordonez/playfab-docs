from playfab_docs.index import write_jsonl
from playfab_docs.snapshot import create_staging, previous_entries, publish, retire_removed


def test_staging_preserves_previous_and_publish_swaps_atomically(tmp_path):
    root = tmp_path / "docs"
    (root / "raw" / "official-guide" / "multiplayer").mkdir(parents=True)
    old = root / "raw" / "official-guide" / "multiplayer" / "lobby.md"
    old.write_text("old", encoding="utf-8")
    write_jsonl(
        root / "reports" / "search_index.jsonl",
        [{"url": "https://example/lobby", "path": "raw/official-guide/multiplayer/lobby.md"}],
    )

    staging = create_staging(root)
    staged_file = staging.raw / "official-guide" / "multiplayer" / "lobby.md"
    assert staged_file.read_text(encoding="utf-8") == "old"
    staged_file.write_text("new", encoding="utf-8")
    publish(staging.root, root)

    assert old.read_text(encoding="utf-8") == "new"
    assert not list(tmp_path.glob(".docs.previous-*"))


def test_removed_manifest_entry_is_retired_not_deleted(tmp_path):
    root = tmp_path / "docs"
    source = root / "raw" / "official-guide" / "multiplayer" / "old.md"
    source.parent.mkdir(parents=True)
    source.write_text("old", encoding="utf-8")
    write_jsonl(
        root / "reports" / "search_index.jsonl",
        [{"url": "https://example/old", "path": "raw/official-guide/multiplayer/old.md"}],
    )
    staging = create_staging(root)

    changes = retire_removed(staging, previous_entries(root), set())

    assert changes[0]["kind"] == "manifest_removed"
    assert not (staging.root / "raw" / "official-guide" / "multiplayer" / "old.md").exists()
    assert (staging.root / "raw" / "_retired" / "official-guide" / "multiplayer" / "old.md").exists()
