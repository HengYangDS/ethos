from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ethos.assistants.playbook_utils import _command_capability_gaps
from ethos.assistants.playbooks import playbooks_report
from ethos.assistants.playbooks import route_playbook
from ethos.assistants.skills.packages import compute_skill_package_digest

if TYPE_CHECKING:
    from pathlib import Path

SKILL = """---
name: {skill_id}
description: Use when governing {subject} work.
---

# {skill_id}

## When to Use

Use this skill for {subject} work.

## Workflow

1. Read repository truth.
2. Run evidence checks.

## Evidence

Run `ethos report --json`.

## Trust Boundary

Repository source, tests, schemas, docs, claims, evidence, and command JSON are truth.
"""


def _write_skill(root: Path, skill_id: str, subject: str, _globs: list[str]) -> None:
    package = root / ".agents" / "skills" / skill_id
    package.mkdir(parents=True)
    (package / "SKILL.md").write_text(
        SKILL.format(skill_id=skill_id, subject=subject),
        encoding="utf-8",
    )
    digest = compute_skill_package_digest(package, ["SKILL.md"])
    (package / "package.toml").write_text(
        f'''
schema_version = 2
id = "{skill_id}"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "ethos.report"
kind = "command_readonly"
command = ["ethos", "report", "--json"]
'''.lstrip(),
        encoding="utf-8",
    )


def _activation(records: list[tuple[str, str, list[str]]]) -> str:
    body = [
        "[meta]",
        "version = 2",
        'source_of_truth = "repository"',
        "",
        "[coverage]",
        'required_primary_subjects = ["one", "two"]',
        'single_owner_subjects = ["one", "two"]',
        "",
    ]
    for skill_id, subject, globs in records:
        glob_lines = "\n".join(f'  "{glob}",' for glob in globs)
        body.append(
            f'''
[[skill]]
id = "{skill_id}"
path = ".agents/skills/{skill_id}/SKILL.md"
package_manifest = ".agents/skills/{skill_id}/package.toml"
subject = "{subject}"
operation = "govern"
authority = "primary"
lifecycle = "active"
subjects = ["{subject}", "changed-scope"]
path_globs = [
{glob_lines}
]
intent_tokens = ["{subject}"]
pre_reads = ["AGENTS.md"]
post_checks = ["ethos report --json"]
commands = ["ethos report"]
boundary = "workflow-package-projection"
'''.strip()
        )
    return "\n\n".join(body) + "\n"


def test_playbooks_report_rejects_duplicate_path_glob(tmp_path: Path) -> None:
    skills_root = tmp_path / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    _write_skill(tmp_path, "one-skill", "one", ["docs/**"])
    _write_skill(tmp_path, "two-skill", "two", ["docs/**"])
    (skills_root / "activation.toml").write_text(
        _activation([("one-skill", "one", ["docs/**"]), ("two-skill", "two", ["docs/**"])]),
        encoding="utf-8",
    )

    report = playbooks_report(tmp_path)

    assert report["ok"] is False
    assert any(
        re.fullmatch(r"skill_portfolio_path_glob_duplicate:docs/\*\*:one-skill,two-skill", gap)
        for gap in report["required_gaps"]
    )


def test_playbooks_report_accepts_disjoint_portfolio_routes(tmp_path: Path) -> None:
    skills_root = tmp_path / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    _write_skill(tmp_path, "one-skill", "one", ["docs/one/**"])
    _write_skill(tmp_path, "two-skill", "two", ["docs/two/**"])
    (skills_root / "activation.toml").write_text(
        _activation([("one-skill", "one", ["docs/one/**"]), ("two-skill", "two", ["docs/two/**"])]),
        encoding="utf-8",
    )

    report = playbooks_report(tmp_path)

    assert report["ok"] is True
    assert report["portfolio_design"]["required_gaps"] == []


def test_legacy_adopter_activation_routes_without_product_v2_strict_gaps(
    tmp_path: Path,
) -> None:
    skills_root = tmp_path / ".agents" / "skills"
    skill_root = skills_root / "example-skill"
    profile = tmp_path / ".ethos" / "profile.toml"
    skill_root.mkdir(parents=True)
    profile.parent.mkdir()
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skill_root / "SKILL.md").write_text(SKILL.format(skill_id="example-skill", subject="docs"))
    profile.write_text(
        'schema_version = 1\n[roots]\nagent_skills = ".agents/skills"\n',
        encoding="utf-8",
    )
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
name = "example-skill"
path_globs = ["docs/**"]
intent_tokens = ["docs"]
pre_reads = ["AGENTS.md"]
post_checks = ["ethos report --json"]
""".lstrip(),
        encoding="utf-8",
    )

    report = playbooks_report(tmp_path)
    route = route_playbook(
        tmp_path,
        "changed-scope",
        require_explicit_subject=True,
        changed_paths=("docs/index.md",),
    )

    assert report["ok"] is True
    assert report["skills"] == ["example-skill"]
    assert route["ok"] is True
    assert [record["id"] for record in route["selected"]] == ["example-skill"]


def test_playbook_command_split_falls_back_for_unclosed_quote() -> None:
    gaps = _command_capability_gaps(
        {"id": "quote-skill", "commands": ["ethos report '"]},
        {"capabilities": [{"command": ["ethos", "report", "'"]}]},
    )

    assert gaps == []
