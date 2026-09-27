"""Qualify native Python starter generation under one formation owner."""

from __future__ import annotations

import os
import subprocess
from contextlib import nullcontext
from importlib import metadata
from stat import S_IFREG
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.repo.starter.formation as formation_effect
import ethos.adapters.repo.starter.generation as generator_effect
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.domain.adoption import adopt_repository
from tests.support.governed_repository import git
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from pathlib import Path


def test_python_library_starter_uses_pinned_native_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One selected domain starter composes with, but does not replace, the foundation."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "A verifiable Python library.",
        "starter": "python-library",
    }
    preview = adopt_repository(target, **request)

    assert preview.verdict == "pass"
    assert not target.exists()
    assert preview.data["source_inputs"]["starter_generator"] == "uv"
    assert preview.data["source_inputs"]["starter_generator_version"] == metadata.version("uv")
    assert {"pyproject.toml", "src/new_project/__init__.py"}.issubset(
        set(preview.data["planned_files"])
    )

    monkeypatch.setattr(
        candidate_projection, "install_hook_launchers", install_fixture_hook_runtime
    )
    applied = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert applied.verdict == "pass"
    assert "A verifiable Python library." in (target / "pyproject.toml").read_text()
    assert (target / "src/new_project/__init__.py").is_file()
    assert git(target, "status", "--porcelain") == ""
    records = [
        item
        for item in read_attestation_set(target)[1]
        if item.predicate == "effect:starter-formation"
    ]
    assert len(records) == 1
    body = records[0].payload.body
    assert body["input"]["sources"]["starter_generator_version"] == metadata.version("uv")
    assert body["output"]["head"] == git(target, "rev-parse", "HEAD")
    assert set(body["output"]["starter_outputs"]) == {
        "pyproject.toml",
        "src/new_project/__init__.py",
        "src/new_project/py.typed",
    }


def test_python_library_changed_input_invalidates_preview(tmp_path: Path) -> None:
    """A reviewed generator output cannot be applied to a changed purpose."""
    target = tmp_path / "new-project"
    preview = adopt_repository(
        target, create=True, purpose="First purpose.", starter="python-library"
    )

    result = adopt_repository(
        target,
        create=True,
        purpose="Revised purpose.",
        starter="python-library",
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert result.required_gaps == ("formation_plan_digest_mismatch",)
    assert not target.exists()


def test_python_library_generator_version_invalidates_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reviewed native-generator identity participates in the plan digest."""
    target = tmp_path / "new-project"
    request = {"create": True, "purpose": "Verifiable changes.", "starter": "python-library"}
    preview = adopt_repository(target, **request)
    observed_version = metadata.version

    def changed_version(name: str) -> str:
        return "changed-generator-version" if name == "uv" else observed_version(name)

    monkeypatch.setattr(formation_effect.metadata, "version", changed_version)
    result = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert result.required_gaps == ("formation_plan_digest_mismatch",)
    assert not target.exists()


def test_python_library_ignores_ambient_uv_generator_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unreviewed host configuration cannot change the selected starter output."""
    target = tmp_path / "new-project"
    request = {"create": True, "purpose": "Verifiable changes.", "starter": "python-library"}
    preview = adopt_repository(target, **request)
    monkeypatch.setenv("UV_INIT_BUILD_BACKEND", "scikit")

    repeated = adopt_repository(target, **request)

    assert repeated.verdict == "pass"
    assert repeated.data["plan_digest"] == preview.data["plan_digest"]
    assert repeated.data["write_plan"] == preview.data["write_plan"]
    assert not target.exists()


def test_unknown_starter_never_invokes_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Starter spelling cannot become arbitrary native-generator flags or tasks."""

    def reject_execution(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unselected generator executed")

    monkeypatch.setattr(generator_effect, "run_command", reject_execution, raising=False)
    target = tmp_path / "new-project"
    result = adopt_repository(
        target,
        create=True,
        purpose="Verifiable changes.",
        starter="python-library --run unsafe",
    )

    assert result.required_gaps == ("formation_starter_unavailable",)
    assert not target.exists()


def test_python_library_generator_failure_is_not_a_retry_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed native tool leaves no target and identifies the repair boundary."""

    def rejected(_root: Path, command: tuple[str, ...], **_kwargs: object) -> object:
        return subprocess.CompletedProcess(command, 1, "", "generator unavailable")

    monkeypatch.setattr(generator_effect, "run_command", rejected)
    target = tmp_path / "new-project"
    result = adopt_repository(
        target, create=True, purpose="Verifiable changes.", starter="python-library"
    )

    assert result.required_gaps == ("formation_starter_generation_failed",)
    assert "Repair" in result.next_action
    assert not target.exists()


def test_python_library_rejects_empty_success_from_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit zero does not prove the selected domain output exists."""

    def empty_success(_root: Path, command: tuple[str, ...], **_kwargs: object) -> object:
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(generator_effect, "run_command", empty_success)
    target = tmp_path / "new-project"
    result = adopt_repository(
        target, create=True, purpose="Verifiable changes.", starter="python-library"
    )

    assert result.required_gaps == ("formation_starter_output_incomplete",)
    assert not target.exists()


def test_python_library_cannot_replace_foundation_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A domain generator cannot silently acquire the foundation's authored files."""

    def overwrite(root: Path, command: tuple[str, ...], **_kwargs: object) -> object:
        (root / "README.md").write_text("replaced\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(generator_effect, "run_command", overwrite)
    target = tmp_path / "new-project"
    result = adopt_repository(
        target, create=True, purpose="Verifiable changes.", starter="python-library"
    )

    assert result.required_gaps == ("formation_starter_overwrote_foundation",)
    assert result.next_action.startswith("Reject")
    assert not target.exists()


def test_python_library_rejects_generator_link_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generator cannot turn foreign bytes into reviewed project output."""
    foreign = tmp_path / "foreign.txt"
    foreign.write_text("preserve", encoding="utf-8")

    def hostile(root: Path, command: tuple[str, ...], **_kwargs: object) -> object:
        try:
            (root / "leak.txt").symlink_to(foreign)
        except OSError:
            pytest.skip("file symlinks unavailable")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(generator_effect, "run_command", hostile)
    target = tmp_path / "new-project"
    result = adopt_repository(
        target, create=True, purpose="Verifiable changes.", starter="python-library"
    )

    assert result.required_gaps == ("formation_starter_output_unsafe",)
    assert foreign.read_text(encoding="utf-8") == "preserve"
    assert not target.exists()


def test_starter_inventory_uses_complete_file_link_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory entry without link counts does not make a new file unsafe."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    incomplete = SimpleNamespace(
        path=str(candidate / "AGENTS.md"),
        stat=lambda **_kwargs: SimpleNamespace(st_mode=S_IFREG, st_nlink=0),
    )
    monkeypatch.setattr(generator_effect.os, "scandir", lambda _path: nullcontext((incomplete,)))
    outputs, _generated, gap, detail = generator_effect.compose_starter(
        candidate, "foundation", "A governed project."
    )

    assert (gap, detail) == ("", "")
    assert set(outputs) == {"AGENTS.md"}


def test_starter_inventory_still_rejects_external_hardlink(tmp_path: Path) -> None:
    """Complete link metadata must retain the external-byte refusal."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    foreign = tmp_path / "foreign.md"
    foreign.write_text("preserve\n", encoding="utf-8")
    try:
        os.link(foreign, candidate / "AGENTS.md")
    except OSError:
        pytest.skip("hardlinks unavailable")

    outputs, _generated, gap, detail = generator_effect.compose_starter(
        candidate, "foundation", "A governed project."
    )

    assert outputs == {}
    assert gap == "formation_starter_output_unsafe"
    assert detail == str(candidate / "AGENTS.md")
    assert foreign.read_text(encoding="utf-8") == "preserve\n"
