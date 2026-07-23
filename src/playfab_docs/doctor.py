from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .index import read_jsonl
from .pipeline import resolve_docs_dir
from .snapshot import abandoned_staging


def inspect_installation(docs_dir: Path, project_dir: Path) -> dict:
    summary_path = docs_dir / "reports" / "summary.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    except json.JSONDecodeError:
        summary = {}
    generated_at = summary.get("generated_at", "")
    stale = False
    if generated_at:
        try:
            built = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            stale = (datetime.now(timezone.utc) - built).days >= 7
        except ValueError:
            stale = True

    skill_paths = [
        project_dir / ".agents" / "skills" / "playfab-expert" / "SKILL.md",
        project_dir / ".claude" / "skills" / "playfab-expert" / "SKILL.md",
        Path.home() / ".agents" / "skills" / "playfab-expert" / "SKILL.md",
    ]
    index = read_jsonl(docs_dir / "reports" / "search_index.jsonl")
    return {
        "docs_dir": str(docs_dir),
        "docs_present": bool(index),
        "indexed_documents": len(index),
        "last_successful_build": generated_at,
        "stale": stale,
        "summary_status": summary.get("status", "missing"),
        "abandoned_staging": [str(path) for path in abandoned_staging(docs_dir)],
        "skill_installations": [str(path) for path in skill_paths if path.exists()],
    }


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description="Inspect a PlayFab Context Builder installation.")
    argument_parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    return argument_parser


def main() -> None:
    args = parser().parse_args()
    report = inspect_installation(resolve_docs_dir(), args.project_dir.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["docs_present"]:
        print("\nNext: uvx playfab-context-builder")
    elif report["stale"]:
        print("\nDocs are older than seven days. Refresh with: uvx playfab-context-builder")
    if not report["skill_installations"]:
        print("\nSkill not found. Install playfab-expert with your agent skill installer.")


if __name__ == "__main__":
    main()
