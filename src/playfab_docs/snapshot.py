from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from .index import read_jsonl
from .models import BuildPaths


def create_staging(root: Path) -> BuildPaths:
    root = root.expanduser().resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.staging-", dir=root.parent))
    if root.exists():
        shutil.copytree(root, staging, dirs_exist_ok=True)
    return BuildPaths.under(staging)


def previous_entries(root: Path) -> dict[str, dict]:
    return {row.get("url", ""): row for row in read_jsonl(root / "reports" / "search_index.jsonl") if row.get("url")}


def retire_removed(staging: BuildPaths, previous: dict[str, dict], current_urls: set[str]) -> list[dict]:
    changes: list[dict] = []
    for url, entry in sorted(previous.items()):
        if url in current_urls:
            continue
        relative = Path(entry.get("path", ""))
        if not relative.parts or relative.parts[0] != "raw":
            continue
        source = staging.root / relative
        if not source.exists():
            continue
        retired_relative = Path("raw") / "_retired" / Path(*relative.parts[1:])
        destination = staging.root / retired_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        changes.append(
            {"kind": "manifest_removed", "url": url, "previous_path": str(relative), "path": str(retired_relative)}
        )
    return changes


def publish(staging_root: Path, target_root: Path) -> None:
    staging_root = staging_root.resolve()
    target_root = target_root.expanduser().resolve()
    if staging_root.parent != target_root.parent or not staging_root.name.startswith(f".{target_root.name}.staging-"):
        raise ValueError("Refusing to publish an unrecognized staging directory")

    backup = target_root.parent / f".{target_root.name}.previous-{os.getpid()}"
    if backup.exists():
        raise FileExistsError(f"Backup path already exists: {backup}")
    if target_root.exists():
        target_root.replace(backup)
    try:
        staging_root.replace(target_root)
    except BaseException:
        if backup.exists() and not target_root.exists():
            backup.replace(target_root)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def abandoned_staging(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    return sorted(root.parent.glob(f".{root.name}.staging-*"))
