import json
from datetime import datetime, timezone

from playfab_docs.doctor import inspect_installation
from playfab_docs.index import write_jsonl


def test_doctor_reports_library_and_agent_skill(tmp_path):
    docs = tmp_path / "docs"
    project = tmp_path / "project"
    skill = project / ".agents" / "skills" / "playfab-expert" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("skill", encoding="utf-8")
    write_jsonl(docs / "reports" / "search_index.jsonl", [{"url": "https://example"}])
    (docs / "reports" / "summary.json").write_text(
        json.dumps({"status": "success", "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}),
        encoding="utf-8",
    )

    report = inspect_installation(docs, project)

    assert report["docs_present"] is True
    assert report["stale"] is False
    assert report["skill_installations"] == [str(skill)]
