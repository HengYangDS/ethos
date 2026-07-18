from __future__ import annotations

from ethos.repository.registry.docs.commands import command_examples_report
from ethos.repository.registry.docs.health import visible_section_gaps_for_registry
from ethos.repository.registry.docs.links import glossary_report
from ethos.repository.registry.docs.links import link_integrity_report
from ethos.repository.registry.docs.links import stable_paths_report


def test_docs_registry_link_integrity_handles_fragments_external_and_encoded_paths(tmp_path):
    guide = tmp_path / "docs" / "guide.md"
    target = tmp_path / "docs" / "target file.md"
    guide.parent.mkdir(parents=True)
    guide.write_text(
        """---
subject: sample:guide
role: guide
state: active
relations: {}
---

# Guide

Status: active.
Purpose: test links.
See also: target.

[local](target%20file.md#target-heading)
[bad-anchor](target%20file.md#missing)
[missing](missing.md)
[external](https://example.com)
[empty]()
[angle](<target file.md>)
""",
        encoding="utf-8",
    )
    target.write_text("# Target Heading\n", encoding="utf-8")

    report = link_integrity_report(tmp_path)

    assert report["ok"] is False
    assert "broken_anchor:docs/guide.md:15:target%20file.md#missing" in report["required_gaps"]
    assert "broken_link:docs/guide.md:16:missing.md" in report["required_gaps"]
    assert all("example.com" not in gap for gap in report["required_gaps"])


def test_docs_registry_command_examples_normalize_env_uv_python_and_scope(tmp_path):
    current = tmp_path / "docs" / "guide.md"
    archive = tmp_path / "docs" / "archive" / "old.md"
    current.parent.mkdir(parents=True)
    archive.parent.mkdir(parents=True)
    current.write_text(
        """---
subject: sample:guide
role: guide
state: active
relations: {}
---

# Guide

Status: active.
Purpose: command examples.
See also: archive.

```bash
env FOO=1 uv run --package ethos ethos prove --json
python -m ethos.cli land --json
ethos unknown-surface --json
custom-tool run
```
""",
        encoding="utf-8",
    )
    archive.write_text("```bash\nlegacy-tool ok\n```\n", encoding="utf-8")

    report = command_examples_report(tmp_path)
    normalized = {item["command"]: item["normalized_command"] for item in report["examples"]}
    scopes = {item["command"]: item["scope"] for item in report["examples"]}

    assert scopes["env FOO=1 uv run --package ethos ethos prove --json"] == "product"
    assert scopes["python -m ethos.cli land --json"] == "product"
    assert scopes["ethos unknown-surface --json"] == "product"
    assert scopes["custom-tool run"] == "product"
    assert scopes["legacy-tool ok"] == "archive"
    assert normalized["env FOO=1 uv run --package ethos ethos prove --json"] == "ethos prove --json"
    assert normalized["python -m ethos.cli land --json"] == "ethos land --json"
    assert (
        "unknown_ethos_command_example:docs/guide.md:17:ethos unknown-surface"
        in report["required_gaps"]
    )
    assert "unknown_command_example:docs/guide.md:18:custom-tool" in report["required_gaps"]
    assert all("legacy-tool" not in gap for gap in report["required_gaps"])


def test_docs_registry_stable_paths_reports_invalid_and_missing_targets(tmp_path):
    meta = tmp_path / "docs" / "_meta"
    meta.mkdir(parents=True)
    (meta / "stable_paths.toml").write_text(
        "[[stable_path]\npath = 'docs/missing.md'\n", encoding="utf-8"
    )

    invalid = stable_paths_report(tmp_path)
    assert invalid == {"ok": False, "required_gaps": ["stable_paths_invalid_toml"]}

    (meta / "stable_paths.toml").write_text(
        "[[stable_path]]\npath = 'docs/missing.md'\n",
        encoding="utf-8",
    )
    report = stable_paths_report(tmp_path)
    assert "stable_path_target_missing:docs/missing.md" in report["required_gaps"]
    assert "stable_path_missing:docs/index.md" in report["required_gaps"]


def test_docs_registry_glossary_and_visible_sections_boundaries(tmp_path):
    active = {"path": "docs/active.md", "state": "active"}
    archived = {"path": "docs/archive/old.md", "state": "archived"}
    evidence = {"path": "evidence/note.md", "state": "active"}
    for entry in (active, archived, evidence):
        path = tmp_path / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Title\nStatus: ok.\n", encoding="utf-8")

    gaps = visible_section_gaps_for_registry(tmp_path, [active, archived, evidence])
    assert gaps == [
        "missing_visible_section:docs/active.md:purpose",
        "missing_visible_section:docs/active.md:see also",
    ]
    assert glossary_report(tmp_path)["required_gaps"] == [
        "glossary_missing:docs/reference/glossary.md"
    ]
