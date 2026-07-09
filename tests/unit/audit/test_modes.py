from __future__ import annotations

import subprocess
from pathlib import Path

import ethos.repository.openspec.audit as openspec_audit
import ethos.surface.cli.root.reference as reference_cli
from ethos.domain.reporting import scoring as reporting_scoring
from ethos.repository import audit
from ethos.repository import audit as repository_audit_module
from ethos.repository.audit import _write_admission_armed_gaps
from ethos.repository.openspec.audit import openspec_shape_report
from ethos.repository.openspec.audit import protected_branch_active_change_required_gaps
from tests.support import ethos_cli_runner


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, text=True, check=True, capture_output=True)


OFFICIAL_OPENSPEC_CONFIG = (
    "schema: spec-driven\n"
    "context: |\n"
    "  Product specification workspace.\n"
    "rules:\n"
    "  proposal:\n"
    "    - Explain the problem and intended change.\n"
    "  specs:\n"
    "    - Use Requirement sections and Scenarios.\n"
    "  tasks:\n"
    "    - Track implementation and verification.\n"
    "  design:\n"
    "    - Record architecture and tradeoffs.\n"
)


def _seed_repo_with_active_openspec_change(repo: Path) -> Path:
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    openspec = repo / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")
    leaked = openspec / "changes" / "leaked-change"
    leaked.mkdir(parents=True)
    (leaked / "proposal.md").write_text("# leaked\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed release root with leaked active openspec carrier")
    return leaked


def test_repository_audit_can_skip_deep_openspec_cli() -> None:
    def forbidden_openspec(_root: Path) -> dict[str, object]:
        raise AssertionError("shallow repository-audit should not run the official OpenSpec CLI")

    report = repository_audit_module.repository_audit(
        Path.cwd(),
        openspec_mode="shape",
        openspec_reporter=forbidden_openspec,
    )

    assert report["ok"] is True
    assert report["openspec"]["mode"] == "shape"


def test_deep_repository_audit_requires_injected_openspec_provider() -> None:
    report = repository_audit_module.repository_audit(Path.cwd(), openspec_mode="deep")

    assert report["ok"] is False
    assert report["openspec"]["required_gaps"] == ["openspec_reporter_not_configured"]


def test_deep_repository_audit_uses_injected_openspec_provider() -> None:
    def fake_openspec(_root: Path) -> dict[str, object]:
        return {"ok": True, "mode": "deep", "required_gaps": []}

    report = repository_audit_module.repository_audit(
        Path.cwd(),
        openspec_mode="deep",
        openspec_reporter=fake_openspec,
    )

    assert report["ok"] is True
    assert report["openspec"]["mode"] == "deep"


def test_quality_release_avoids_full_repository_audit(monkeypatch) -> None:
    def forbidden_repository_audit(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("release file readiness should not run full repository-audit")

    monkeypatch.setattr(repository_audit_module, "repository_audit", forbidden_repository_audit)

    payload = ethos_cli_runner.run_ethos("quality", "release", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality release"


def test_default_prove_uses_shallow_repository_audit(monkeypatch) -> None:
    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("default proof readiness should not run deep OpenSpec validation")

    monkeypatch.setattr(
        reference_cli,
        "openspec_governance_report",
        forbidden_openspec,
    )

    payload = ethos_cli_runner.run_ethos("prove", "--json")

    assert payload["ok"] is True
    assert payload["data"]["repository_audit"]["openspec"]["mode"] == "shape"


def test_report_uses_shallow_repository_audit(monkeypatch) -> None:
    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("scorecard report should not run deep OpenSpec validation")

    monkeypatch.setattr(
        reference_cli,
        "openspec_governance_report",
        forbidden_openspec,
    )
    monkeypatch.setattr(
        reporting_scoring,
        "coverage_quality_report",
        lambda _repo: {"ok": True, "state": "clean", "required_gaps": []},
    )

    payload = ethos_cli_runner.run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["repository_audit"]["openspec"]["mode"] == "shape"


def test_openspec_shape_flags_completed_but_unarchived_change(tmp_path: Path, monkeypatch) -> None:
    """A change whose tasks are all complete but which is still in changes/ (not
    archived) is a carrier masquerading as active — the always-run shape audit must
    flag it from ETHOS's own tasks-complete signal, not only at land --closeout."""
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")
    change = openspec / "changes" / "done-change"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text("## 1\n\n- [x] a\n- [x] b\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(openspec_audit.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = openspec_audit.openspec_shape_report(tmp_path)

    assert report["ok"] is False
    assert "openspec_completed_change_unarchived:done-change" in report["required_gaps"]


def test_openspec_shape_flags_metadata_keys_before_editor_parse(tmp_path: Path) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")
    change = openspec / "changes" / "active-change"
    change.mkdir(parents=True)
    (change / ".openspec.yaml").write_text(
        "schema: spec-driven\ngoal: should fail before PyCharm parses it\n",
        encoding="utf-8",
    )

    report = openspec_shape_report(tmp_path)

    assert report["ok"] is False
    assert (
        "openspec_metadata_key_unsupported:goal:"
        "openspec/changes/active-change/.openspec.yaml" in report["required_gaps"]
    )
    metadata = report["metadata_compatibility"]
    assert metadata["ok"] is False
    assert metadata["summary"]["issue_count"] == 1


def test_openspec_shape_allows_in_progress_and_archived_changes(tmp_path: Path) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")
    # in-progress change (a box unchecked) is legitimately active
    active = openspec / "changes" / "wip"
    active.mkdir(parents=True)
    (active / "tasks.md").write_text("- [x] a\n- [ ] b\n", encoding="utf-8")
    # archived completed change is fine
    archived = openspec / "changes" / "archive" / "2026-01-01-old"
    archived.mkdir(parents=True)
    (archived / "tasks.md").write_text("- [x] a\n", encoding="utf-8")

    report = openspec_shape_report(tmp_path)

    assert not any("unarchived" in gap for gap in report["required_gaps"])


def test_openspec_shape_flags_removed_accepted_spec_obligations(
    tmp_path: Path, monkeypatch
) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = (
            "diff --git a/openspec/specs/repository-governance/spec.md "
            "b/openspec/specs/repository-governance/spec.md\n"
            "+++ b/openspec/specs/repository-governance/spec.md\n"
            "@@ -1 +0,0 @@\n"
            "- **AND** existing branch role obligations remain visible\n"
            "- plain explanatory sentence"
        )
        stderr = ""

    monkeypatch.setattr(audit.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = audit.openspec_shape_report(tmp_path)

    assert report["ok"] is False
    assert (
        "openspec_spec_obligation_removed:openspec/specs/repository-governance/spec.md:"
        "**AND** existing branch role obligations remain visible" in report["required_gaps"]
    )
    assert not any("plain explanatory sentence" in gap for gap in report["required_gaps"])


def test_openspec_shape_allows_added_or_unchanged_spec_obligations(
    tmp_path: Path, monkeypatch
) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = (
            "diff --git a/openspec/specs/repository-governance/spec.md "
            "b/openspec/specs/repository-governance/spec.md\n"
            "+++ b/openspec/specs/repository-governance/spec.md\n"
            "@@ -1,0 +1 @@\n"
            "+ **AND** new obligations are fine"
        )
        stderr = ""

    monkeypatch.setattr(audit.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = audit.openspec_shape_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_repository_audit_flags_unarmed_write_admission(tmp_path, monkeypatch) -> None:
    """The write-admission moat must be armed (git core.hooksPath -> .githooks) for the
    always-run audit to pass. An ETHOS-admission repo (has .githooks/pre-commit) whose
    hooksPath is unset is a governance runtime green about its own ungated writes."""
    hook = tmp_path / ".githooks" / "pre-commit"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / ".githooks" / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / ".githooks" / "reference-transaction").write_text("#!/bin/sh\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    # hooksPath unset -> flagged
    assert "write_admission_not_armed:core.hooksPath" in _write_admission_armed_gaps(tmp_path)

    # armed -> clean
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=tmp_path, check=True)
    assert _write_admission_armed_gaps(tmp_path) == []


def test_write_admission_check_is_silent_for_non_admission_repos(tmp_path) -> None:
    # A repo without the .githooks/pre-commit script is not an ETHOS-admission repo;
    # nothing to arm, so no gap (do not punish plain adopters).
    assert _write_admission_armed_gaps(tmp_path) == []


def test_openspec_shape_surfaces_active_change_on_non_current_protected_branch(
    tmp_path: Path,
) -> None:
    """Protected branch trees are visible signals even when not current truth."""
    repo = tmp_path / "repo"
    leaked = _seed_repo_with_active_openspec_change(repo)

    _git(repo, "checkout", "-b", "dev")
    (leaked / "proposal.md").unlink()
    leaked.rmdir()
    archive = repo / "openspec" / "changes" / "archive" / "2026-01-01-leaked-change"
    archive.mkdir(parents=True)
    (archive / "proposal.md").write_text("# archived\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "archive change on accepted root")

    report = openspec_shape_report(repo)

    gap = "openspec_protected_branch_active_change_unarchived:main:release_root:leaked-change"
    assert report["ok"] is True
    assert gap in report["advisory_gaps"]
    assert gap not in report["required_gaps"]


def test_release_readiness_blocks_active_change_on_non_current_release_root(
    tmp_path: Path,
) -> None:
    """Publication cannot ignore a release-root active OpenSpec carrier."""
    repo = tmp_path / "repo"
    leaked = _seed_repo_with_active_openspec_change(repo)

    _git(repo, "checkout", "-b", "dev")
    (leaked / "proposal.md").unlink()
    leaked.rmdir()
    archive = repo / "openspec" / "changes" / "archive" / "2026-01-01-leaked-change"
    archive.mkdir(parents=True)
    (archive / "proposal.md").write_text("# archived\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "archive change on accepted root")

    assert protected_branch_active_change_required_gaps(repo, current_branch="dev") == [
        "openspec_protected_branch_active_change_unarchived:main:release_root:leaked-change"
    ]


def test_openspec_shape_blocks_active_change_on_current_release_root(tmp_path: Path) -> None:
    """The current release root cannot retain active OpenSpec carriers."""
    repo = tmp_path / "repo"
    _seed_repo_with_active_openspec_change(repo)

    report = openspec_shape_report(repo)

    assert report["ok"] is False
    assert "openspec_active_change_unarchived:leaked-change:release_root" in report["required_gaps"]
    assert not report["advisory_gaps"]


def test_openspec_shape_rejects_legacy_project_version_config(tmp_path: Path, monkeypatch) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text("project: ethos\nversion: 1\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(openspec_audit.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = openspec_audit.openspec_shape_report(tmp_path)

    assert report["ok"] is False
    assert "openspec_config_schema_missing" in report["required_gaps"]
    assert "openspec_config_context_missing" in report["required_gaps"]
    assert "openspec_config_rules_missing" in report["required_gaps"]


def test_openspec_shape_rejects_invalid_official_config_yaml(tmp_path: Path, monkeypatch) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text("schema: [unterminated\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(openspec_audit.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = openspec_audit.openspec_shape_report(tmp_path)

    assert report["ok"] is False
    assert any(gap.startswith("openspec_config_invalid:") for gap in report["required_gaps"])


def test_openspec_shape_accepts_official_spec_driven_config(tmp_path: Path, monkeypatch) -> None:
    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text(OFFICIAL_OPENSPEC_CONFIG, encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(openspec_audit.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = openspec_audit.openspec_shape_report(tmp_path)

    assert report["ok"] is True
    assert report["official_config"]["ok"] is True
