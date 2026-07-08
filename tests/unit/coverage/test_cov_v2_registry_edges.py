# ruff: noqa: TC002, TC003
"""Coverage-closure edge tests for the repository registry cluster (docs, commands, profiles).

Each test drives a specific uncovered branch identified in the v2 100% campaign. Line
numbers in comments refer to the source files at dev commit 1966465.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.repository.registry import commands
from ethos.repository.registry import docs
from ethos.repository.registry import profiles


def test_front_matter_flushes_nested_block_before_next_top_level_key(tmp_path: Path) -> None:
    # A nested block (indented continuation) followed by another top-level key forces the
    # mid-loop flush at docs.py:136-138 (join the accumulated nested lines, reset buffer)
    # rather than the post-loop flush at 144-145.
    path = tmp_path / "fm.md"
    path.write_text(
        "---\nrelations:\n  - a\n  - b\nsubject: topic\nrole: guide\nstate: active\n---\n# Body\n",
        encoding="utf-8",
    )

    values = docs._front_matter(path)

    assert values["relations"] == "- a; - b"
    assert values["subject"] == "topic"
    assert values["state"] == "active"


def test_taxonomy_returns_empty_on_malformed_toml(tmp_path: Path) -> None:
    # A present-but-invalid taxonomy.toml raises TOMLDecodeError -> docs.py:174-175 returns {}.
    meta = tmp_path / "docs" / "_meta"
    meta.mkdir(parents=True)
    (meta / "taxonomy.toml").write_text("[states\nallowed = ['active'\n", encoding="utf-8")

    assert docs._taxonomy(tmp_path) == {}


def test_visible_section_gaps_skips_registry_entry_without_file(tmp_path: Path) -> None:
    # An entry that requires visible sections (active, non-observational) but whose file is
    # absent hits the `if not path.exists(): continue` guard at docs.py:227, yielding no gap.
    registry = [{"path": "docs/ghost.md", "state": "active"}]

    assert docs._visible_section_gaps(tmp_path, registry) == []


def test_command_root_strips_residual_env_and_assignment_tokens() -> None:
    # Normalization strips one leading `env` + assignments; a doubled `env` leaves a residual
    # `env` and assignment for _command_root's own stripping at docs.py:380 (env token) and
    # docs.py:382 (assignment token) before returning the real root.
    assert docs._command_root("env env FOO=1 bar") == "bar"


def test_ethos_command_helpers_reject_non_ethos_invocations() -> None:
    # A command whose first token is not `ethos` short-circuits in each helper:
    # docs.py:404 (_ethos_command_key -> ""), docs.py:413 (_known_ethos_command -> False),
    # docs.py:517 (_best_ethos_command_key -> "").
    assert docs._ethos_command_key("git status") == ""
    assert docs._known_ethos_command("git status") is False
    assert docs._best_ethos_command_key("git status") == ""


def test_command_examples_flags_retired_public_root(tmp_path: Path) -> None:
    # A retired public root (`proof`) inside a bash fence triggers the retired-command branch
    # at docs.py:468.
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nproof legacy objective\n```\n",
        encoding="utf-8",
    )

    report = docs.command_examples_report(tmp_path)

    assert "retired_command_example:README.md:2:proof" in report["required_gaps"]


def test_bash_logical_commands_flush_on_fence_close_and_eof(tmp_path: Path) -> None:
    # A continued command (trailing backslash, empty buffer never terminated) followed by the
    # closing fence flushes at docs.py:492-494; the same command left with the fence unclosed
    # flushes at end-of-file via docs.py:510.
    closed = tmp_path / "closed.md"
    closed.write_text("```bash\nethos prove \\\n```\n", encoding="utf-8")
    unclosed = tmp_path / "unclosed.md"
    unclosed.write_text("```bash\nethos prove \\\n", encoding="utf-8")

    assert docs._bash_logical_commands(closed) == [(2, "ethos prove")]
    assert docs._bash_logical_commands(unclosed) == [(2, "ethos prove")]


def test_command_surface_policy_returns_empty_on_malformed_toml(tmp_path: Path) -> None:
    # A present-but-invalid command-surface.toml raises TOMLDecodeError -> commands.py:86-87
    # returns {}.
    surface = tmp_path / "rules" / "ethos"
    surface.mkdir(parents=True)
    (surface / "command-surface.toml").write_text("[policy\ngoverned_docs = [\n", encoding="utf-8")

    assert commands._command_surface_policy(tmp_path) == {}


def test_policy_doc_paths_skips_retired_reference_doc(tmp_path: Path) -> None:
    # With an explicit governed-doc glob selector, a doc listed in retired_reference_docs is
    # skipped by the `continue` at commands.py:120 while a sibling live doc is selected.
    surface = tmp_path / "rules" / "ethos"
    surface.mkdir(parents=True)
    (surface / "command-surface.toml").write_text(
        '[policy]\ngoverned_doc_globs = ["docs/*.md"]\nretired_reference_docs = ["docs/retired.md"]\n',
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "retired.md").write_text("`proof` reference\n", encoding="utf-8")
    (tmp_path / "docs" / "live.md").write_text("# live\n", encoding="utf-8")

    selected = {
        path.relative_to(tmp_path).as_posix() for path in commands._policy_doc_paths(tmp_path)
    }

    assert "docs/retired.md" not in selected
    assert "docs/live.md" in selected


def test_scan_retired_prefixes_detects_backtick_quoted_mention(tmp_path: Path) -> None:
    # A retired command prefix quoted in backticks in prose (outside any fence) is caught by the
    # backtick-mention branch at commands.py:181.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "pref.md").write_text(
        "Do not use `ethos governance` anymore.\n",
        encoding="utf-8",
    )

    mentions = commands._scan_retired_public_command_prefixes(tmp_path)

    assert mentions == ["docs/pref.md:1:ethos governance"]


def test_governance_profile_report_flags_mismatch_missing_and_committee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Drive the unhappy paths in governance_profile_report: a non-reference profile whose shared
    # kernel field differs appends at profiles.py:191; empty allowed-difference fields append at
    # profiles.py:196; a below-minimum committee role count appends at profiles.py:199.
    reference = profiles.GovernanceProfile(id="reference", mode="m", subject="s")
    diverging = profiles.GovernanceProfile(
        id="diverging", mode="m", subject="s", capability_graph=("X",)
    )
    monkeypatch.setattr(profiles, "canonical_governance_profiles", lambda: (reference, diverging))
    monkeypatch.setattr(
        profiles,
        "governance_committee_profile",
        lambda: {
            "role_count": 1,
            "minimum_role_count": 4,
            "roles": [],
            "consensus_gate": {},
        },
    )

    report = profiles.governance_profile_report()
    gaps = report["required_gaps"]

    assert "diverging:capability_graph_mismatch" in gaps
    assert "reference:authority_binding_missing" in gaps
    assert "campaign_committee_role_count_below_minimum" in gaps
    assert report["ok"] is False
    assert report["isomorphic"] is False
