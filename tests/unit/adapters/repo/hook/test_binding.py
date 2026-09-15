"""Tests for immutable hook binding and commit-policy capability projection."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import cast

import pytest
import tomli_w

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.hook.binding as hook_contract
import ethos.adapters.repo.hook.observation as hook_binding
import ethos.adapters.repo.runtime.authority as runtime_authority
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import load_hook_contract
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import runtime_command
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_test_profile
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from ethos.adapters.repo.hook.observation import CommitPolicyEnforcement

_POLICY = (
    '[commit_policy]\nsubject_pattern = "fix: .+"\n'
    'signing_required = false\nsigning_format = "ssh"\n'
)


def _fixture(tmp_path: Path, *, policy: str | None = None) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    install_fixture_hook_runtime(repo)
    if policy is not None:
        path = repo / ".ethos/workspace.toml"
        path.parent.mkdir()
        path.write_text(policy, encoding="utf-8")
    configured = git_process(repo, "config", "--path", "--get", "core.hooksPath")
    return repo, Path(configured.stdout.strip())


def _capability(repo: Path) -> tuple[dict[str, Any], CommitPolicyEnforcement]:
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    return projected, cast(
        "CommitPolicyEnforcement", projected["data"]["commit_policy_enforcement"]
    )


def test_hook_binding_tracks_exact_generation_and_expected_build(tmp_path: Path) -> None:
    repo, generation = _fixture(tmp_path)

    observed = hook_runtime_binding(repo)
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    stale = hook_runtime_binding(repo, expected_build=runtime_build("c" * 40, "d" * 40))

    assert observed["hooks_path"] == generation.as_posix()
    assert observed["required_gaps"] == []
    assert projected["data"]["hook_runtime"] == observed
    assert (stale["expected_source_commit"], stale["expected_source_tree"]) == (
        "c" * 40,
        "d" * 40,
    )
    assert stale["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert stale["next_action"].endswith(f"hook install --root {repo} --json")
    assert Path(stale["next_action"].split()[0]).resolve() == Path(sys.executable).resolve()


@pytest.mark.parametrize("launcher", ["commit-msg", "pre-push"])
def test_declared_policy_reports_each_missing_transport(tmp_path: Path, launcher: str) -> None:
    repo, generation = _fixture(tmp_path, policy=_POLICY)
    (generation / launcher).unlink()

    projected, capability = _capability(repo)

    gap = f"write_admission_not_armed:{launcher}_launcher_missing"
    assert capability["state"] == "unarmed"
    assert capability["declaration"]["subject_pattern"] == "fix: .+"
    assert capability["required_gaps"] == [gap]
    assert gap in projected["required_gaps"]
    assert capability["next_action"] == runtime_command(
        repo, "hook", "install", "--root", repo.as_posix(), "--json"
    )


@pytest.mark.parametrize(
    ("policy", "state", "declared", "message", "push"),
    [
        (_POLICY, "armed", "true", "armed", "armed"),
        (None, "not_declared", "false", "not_required", "not_required"),
        (
            (
                '[commit_policy]\nsubject_pattern = "["\n'
                'signing_required = false\nsigning_format = "ssh"\n'
            ),
            "invalid",
            "invalid",
            "unknown",
            "unknown",
        ),
    ],
)
def test_commit_policy_capability_state_matrix(
    tmp_path: Path,
    policy: str | None,
    state: str,
    declared: Literal["true", "false", "invalid"],
    message: str,
    push: str,
) -> None:
    repo, _generation = _fixture(tmp_path, policy=policy)

    projected, capability = _capability(repo)

    assert capability["state"] == state
    expected_declared = {"true": True, "false": False, "invalid": None}[declared]
    assert capability["declared"] is expected_declared
    assert capability["commit_message_transport"] == message
    assert capability["push_range_enforcement"] == push
    if state == "invalid":
        assert projected["verdict"] == "block"
        assert capability["required_gaps"][0].startswith("commit_policy_subject_pattern_invalid:")


def test_candidate_hook_semantics_remain_pending_until_acceptance(tmp_path: Path) -> None:
    repo, _generation = _fixture(tmp_path, policy=_POLICY)
    runtime = hook_runtime_binding(repo)
    runtime["scripts"] = ["pre-commit", "pre-push", "reference-transaction"]
    capability = hook_binding.commit_policy_enforcement(repo, runtime)

    assert capability["state"] == "pending_acceptance"
    assert capability["required_gaps"] == []
    assert capability["next_action"] == ""


def test_armed_transport_does_not_claim_signature_trust_is_ready(tmp_path: Path) -> None:
    repo, _generation = _fixture(tmp_path, policy=_POLICY.replace("false", "true"))
    _report, capability = _capability(repo)
    assert capability["commit_message_transport"] == "armed"
    assert capability["push_range_enforcement"] == "armed"
    assert capability["state"] == "unready"
    assert capability["required_gaps"] == ["commit_trust_anchor_missing"]
    assert capability["signature_trust"] == {
        "state": "unready",
        "anchor": "",
        "required_gaps": ["commit_trust_anchor_missing"],
    }
    assert "gpg.ssh.allowedSignersFile" in capability["next_action"]


def test_stale_runtime_unarms_both_policy_transports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _generation = _fixture(tmp_path, policy=_POLICY)
    monkeypatch.setattr(
        runtime_authority,
        "expected_runtime_build",
        lambda _repo: (runtime_build("c" * 40, "d" * 40), tmp_path / "accepted"),
    )

    projected, capability = _capability(repo)

    gap = "write_admission_not_armed:runtime_build_stale"
    assert capability["state"] == "unarmed"
    assert capability["commit_message_transport"] == "unarmed"
    assert capability["push_range_enforcement"] == "unarmed"
    assert capability["required_gaps"] == [gap]
    assert projected["required_gaps"].count(gap) == 1
    assert capability["next_action"].startswith((tmp_path / "accepted/.venv/bin/python").as_posix())


@pytest.mark.parametrize("adopted", [False, True])
@pytest.mark.parametrize(
    "condition", ["current", "stale", "missing-launcher", "damaged-selector", "unknown"]
)
def test_status_preserves_runtime_readiness_without_commit_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    adopted: bool,
    condition: str,
) -> None:
    """An optional policy cannot hide the installed runtime's independent gaps."""
    repo, generation = _fixture(tmp_path)
    if adopted:
        write_test_profile(repo)
    if condition == "stale":
        monkeypatch.setattr(
            runtime_authority,
            "expected_runtime_build",
            lambda _repo: (runtime_build("c" * 40, "d" * 40), tmp_path / "accepted"),
        )
    elif condition == "missing-launcher":
        (generation / "pre-commit").unlink()
    elif condition == "damaged-selector":
        (Path(git_common_dir(repo)) / "ethos/runtime/CURRENT").write_text("invalid\n")
    elif condition == "unknown":
        reader = Path.read_text

        def unreadable(path: Path, *args, **kwargs):
            if path.name == "binding.toml" and path.is_relative_to(repo):
                message = "selected_declaration_unreadable"
                raise PermissionError(message)
            return reader(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", unreadable)

    projected, capability = _capability(repo)
    runtime = projected["data"]["hook_runtime"]

    assert capability["state"] == "not_declared"
    assert capability["required_gaps"] == []
    assert capability["next_action"] == ""
    if condition == "current":
        assert runtime["current"] is True
        assert not any(
            gap.startswith("write_admission_not_armed:") for gap in projected["required_gaps"]
        )
    else:
        gap = {
            "stale": "write_admission_not_armed:runtime_build_stale",
            "missing-launcher": "write_admission_not_armed:pre-commit_launcher_missing",
            "damaged-selector": "write_admission_not_armed:runtime_current",
            "unknown": "write_admission_not_armed:runtime_hook_contract_unavailable",
        }[condition]
        assert runtime["current"] is False
        assert runtime["required_gaps"] == [gap]
        assert projected["required_gaps"].count(gap) == 1
        assert projected["verdict"] != "pass"
        assert projected["next_action"] == runtime["next_action"]
        assert projected["user_decision_required"] is False


@pytest.mark.parametrize("adopted", [False, True])
def test_status_requires_installation_only_for_an_adopted_repository(
    tmp_path: Path, *, adopted: bool
) -> None:
    """A missing adopter runtime blocks readiness, but inspection is not adoption."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    if adopted:
        write_test_profile(repo)

    projected, capability = _capability(repo)
    runtime = projected["data"]["hook_runtime"]

    assert capability["state"] == "not_declared"
    assert runtime["current"] is False
    if adopted:
        assert "write_admission_not_armed:runtime_current" in projected["required_gaps"]
        assert projected["next_action"] == runtime["next_action"]
        assert projected["verdict"] == "block"
    else:
        assert not any(
            gap.startswith("write_admission_not_armed:") for gap in projected["required_gaps"]
        )
        assert "hook install" not in projected["next_action"]


def test_adopted_status_moves_from_ready_to_stale_without_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fully ready adopter must lose PASS when only its expected runtime advances."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    before, policy = _capability(repo)
    assert (before["verdict"], before["required_gaps"], before["next_action"]) == ("pass", [], "")
    assert policy["state"] == "not_declared"
    monkeypatch.setattr(
        runtime_authority,
        "expected_runtime_build",
        lambda _repo: (runtime_build("c" * 40, "d" * 40), tmp_path / "accepted"),
    )

    after, _policy = _capability(repo)

    assert after["verdict"] == "block"
    assert after["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert after["next_action"] == after["data"]["hook_runtime"]["next_action"]
    assert "hook install" in after["next_action"]


@pytest.mark.parametrize("payload", [b"\xff", b"#!/bin/sh\nexit 0\n"])
def test_launcher_drift_fails_closed(tmp_path: Path, payload: bytes) -> None:
    repo, generation = _fixture(tmp_path)
    (generation / "pre-push").write_bytes(payload)

    observed = hook_runtime_binding(repo)

    assert observed["required_gaps"] == ["write_admission_not_armed:pre-push_launcher_drift"]


@pytest.mark.parametrize(
    "defect",
    ["toml", "extra", "empty", "duplicate", "name", "platforms", "absolute", "parent", "template"],
)
def test_malformed_hook_declaration_is_rejected(tmp_path: Path, defect: str) -> None:
    """Only the closed data grammar may produce launcher bytes."""
    original = Path(hook_contract.__file__).with_suffix(".toml")
    values = tomllib.loads(original.read_text())
    if defect == "extra":
        values["surprise"] = True
    elif defect == "empty":
        values["scripts"] = []
    elif defect == "duplicate":
        values["scripts"] = ["pre-commit", "pre-commit"]
    elif defect == "name":
        values["scripts"] = ["../unowned"]
    elif defect == "platforms":
        values["python"] = {"posix": "python/bin/python"}
    elif defect in {"absolute", "parent"}:
        values["python"]["posix"] = "/external/python" if defect == "absolute" else "../python"
    elif defect == "template":
        values["launcher"] = "#!/bin/sh\nexit 0\n"
    declaration = tmp_path / "binding.toml"
    declaration.write_text("invalid = [" if defect == "toml" else tomli_w.dumps(values))
    with pytest.raises(ValueError, match=r"Invalid value|hook_launcher_declaration_invalid"):
        hook_contract.load_hook_contract(declaration)


def test_selected_hook_declaration_read_failure_is_nonarming(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unavailable current bytes remain unknown rather than using another package."""
    repo, _generation = _fixture(tmp_path)
    before = hook_runtime_binding(repo)
    reader = Path.read_text
    paths = []

    def unreadable(path: Path, *args, **kwargs):
        if path.name == "binding.toml" and path.is_relative_to(repo):
            paths.append(path)
            message = "selected_declaration_unreadable"
            raise PermissionError(message)
        return reader(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", unreadable)
        observed = hook_runtime_binding(repo)
    assert len(paths) == 1
    assert observed["current"] is False
    assert observed["state"] == "unknown"
    assert observed["required_gaps"] == [
        "write_admission_not_armed:runtime_hook_contract_unavailable"
    ]
    assert observed["contract_observation"] == {
        "state": "unknown",
        "reason": "runtime_hook_contract_unavailable",
        "path": paths[0].as_posix(),
        "cause": "selected_declaration_unreadable",
        "effect_attempted": False,
    }
    assert "status" in observed["next_action"]
    assert hook_runtime_binding(repo) == before


@pytest.mark.parametrize("configured_form", ["absolute", "relative"])
def test_symlinked_generation_is_rejected(tmp_path: Path, configured_form: str) -> None:
    repo, generation = _fixture(tmp_path)
    alias = generation.with_name("f" * 64)
    alias.symlink_to(generation, target_is_directory=True)
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    configured = (
        alias.relative_to(repo).as_posix() if configured_form == "relative" else alias.as_posix()
    )
    assert git_process(repo, "config", "--worktree", "core.hooksPath", configured).returncode == 0

    assert "write_admission_not_armed:core.hooksPath" in hook_runtime_binding(repo)["required_gaps"]


def test_generation_root_and_external_path_are_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    common = Path(git_common_dir(repo))
    real = common / "external-hooks"
    root = common / "ethos/hooks"
    real.mkdir()
    root.parent.mkdir(parents=True)
    root.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        hook_activation.materialize_hook_launchers(root)
    root.unlink()
    external = tmp_path / "external-hooks"
    external.mkdir()
    assert git_process(repo, "config", "core.hooksPath", external.as_posix()).returncode == 0
    assert "write_admission_not_armed:core.hooksPath" in hook_runtime_binding(repo)["required_gaps"]


def test_binding_primitives_and_unavailable_source_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="hook_name_invalid"):
        hook_contract.hook_launcher("post")
    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_contract.hook_generation_digest({"pre-commit": "only"})

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=True)
    generation = repo / ".git/ethos/hooks" / ("a" * 64)
    generation.mkdir(parents=True)
    subprocess.run(("git", "config", "core.hooksPath", generation.as_posix()), cwd=repo, check=True)
    monkeypatch.setattr(hook_binding, "_selected_runtime", lambda *_args: (None, "runtime_current"))
    monkeypatch.setattr(
        runtime_authority,
        "expected_runtime_build",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )
    monkeypatch.setattr(
        runtime_authority,
        "expected_runtime_source",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )

    assert (
        "write_admission_not_armed:runtime_expected_source_unavailable"
        in (hook_runtime_binding(repo)["required_gaps"])
    )


def test_pure_hook_query_does_not_initialize_runtime_or_policy() -> None:
    program = """
import json, sys
from ethos.adapters.repo.hook.binding import HOOK_NAMES, hook_generation_digest, hook_launcher
launchers = {name: hook_launcher(name) for name in HOOK_NAMES}
print(json.dumps({"digest": hook_generation_digest(launchers), "modules": sorted(sys.modules)}))
"""
    result = subprocess.run(
        (sys.executable, "-B", "-I", "-c", program),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    observed = json.loads(result.stdout)
    expected = hook_contract.hook_generation_digest(
        {name: hook_contract.hook_launcher(name) for name in hook_contract.HOOK_NAMES}
    )
    assert observed["digest"] == expected
    assert not {
        "ethos.adapters.repo.runtime.authority",
        "ethos.adapters.repo.runtime.selection",
        "ethos.repository.profile",
        "pydantic",
        "filelock",
    }.intersection(observed["modules"])


@pytest.mark.parametrize("platform", ["posix", "nt"])
def test_declaration_binds_native_protocol_on_each_platform(platform: str) -> None:
    """Every platform binds the selected package without the interactive CLI."""
    contract = hook_contract.load_hook_contract(platform_name=platform)
    python = "python/bin/python" if platform == "posix" else "python/python.exe"
    assert contract["scripts"] == ("commit-msg", "pre-commit", "pre-push", "reference-transaction")
    for name, launcher in contract["launchers"].items():
        assert launcher.endswith(
            f'exec "$RUNTIME/{python}" -B -I -m ethos.adapters.repo.hook.protocol {name} "$@"\n'
        )


def test_hook_declaration_rejects_symlink_and_unknown_platform(tmp_path: Path) -> None:
    declaration = Path(hook_contract.__file__).with_suffix(".toml")
    link = tmp_path / "binding.toml"
    link.symlink_to(declaration)
    with pytest.raises(ValueError, match="hook_launcher_declaration_invalid"):
        hook_contract.load_hook_contract(link)
    with pytest.raises(ValueError, match="hook_launcher_platform_invalid"):
        hook_contract.load_hook_contract(platform_name="unknown")


def test_predeclaration_runtime_derives_successor_install_not_old_reinstall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing package contract must not send migration back to the old reader."""
    repo, _generation = _fixture(tmp_path)
    reader = Path.read_text

    def missing(path: Path, *args, **kwargs):
        if path.name == "binding.toml" and path.is_relative_to(repo):
            raise FileNotFoundError(path)
        return reader(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", missing)
    observed = hook_runtime_binding(repo)
    assert observed["current"] is False
    assert observed["required_gaps"] == ["write_admission_not_armed:runtime_hook_contract_missing"]
    command = shlex.split(observed["next_action"])
    assert command[:7] == [sys.executable, "-B", "-I", "-m", "ethos.cli", "hook", "install"]
    assert command[0] != observed["python"]


def test_selected_declaration_drift_cannot_borrow_the_invoking_contract(tmp_path: Path) -> None:
    """An inventory mismatch must unarm hooks before consuming changed package data."""
    repo, _generation = _fixture(tmp_path)
    before = hook_runtime_binding(repo)
    selected = Path(before["runtime_manifest_path"]).parent
    declaration = next(selected.glob("python/**/ethos/adapters/repo/hook/binding.toml"))
    original = declaration.read_bytes()
    changed = original.replace(b"@HOOK@", b"wrong")
    assert changed != original
    declaration.write_bytes(changed)
    observed = hook_runtime_binding(repo)
    assert observed["current"] is False
    assert (
        "write_admission_not_armed:runtime_schema_migration_required" in observed["required_gaps"]
    )
    declaration.write_bytes(original)
    assert hook_runtime_binding(repo) == before


def test_hook_launcher_uses_git_shell_and_current_runtime_selector() -> None:
    text = hook_launcher("pre-commit")

    assert 'HOOK_DIR=${0%/*}; [ "$HOOK_DIR" = "$0" ] && HOOK_DIR=.' in text
    assert 'HOOK_DIR=$(CDPATH= cd "$HOOK_DIR" && pwd)' in text
    assert 'RUNTIME_ROOT="$HOOK_DIR/../../runtime"' in text
    assert 'CURRENT="$RUNTIME_ROOT/CURRENT"' in text
    assert (
        'exec "$RUNTIME/python/bin/python" -B -I '
        '-m ethos.adapters.repo.hook.protocol pre-commit "$@"'
    ) in text


def test_hook_launcher_enters_the_selected_runtime_without_ambient_path(tmp_path: Path) -> None:
    digest = "a" * 64
    hooks = tmp_path / "ethos/hooks/generation"
    runtime = tmp_path / "ethos/runtime" / digest / "python/bin/python"
    hooks.mkdir(parents=True)
    runtime.parent.mkdir(parents=True)
    (tmp_path / "ethos/runtime/CURRENT").write_text(f"{digest}\n", encoding="ascii")
    runtime.write_text('#!/bin/sh\nprintf "%s\\n" "$*"\n', encoding="utf-8")
    runtime.chmod(0o755)
    launcher = hooks / "pre-commit"
    launcher.write_text(hook_launcher("pre-commit"), encoding="utf-8")
    launcher.chmod(0o755)

    completed = subprocess.run(
        (launcher.as_posix(), "argument"),
        check=False,
        capture_output=True,
        env={"PATH": ""},
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "-B -I -m ethos.adapters.repo.hook.protocol pre-commit argument\n"


def test_windows_hook_launcher_uses_the_standalone_runtime_python() -> None:
    text = load_hook_contract(platform_name="nt")["launchers"]["pre-commit"]

    assert (
        'exec "$RUNTIME/python/python.exe" -B -I '
        '-m ethos.adapters.repo.hook.protocol pre-commit "$@"'
    ) in text
    assert "Scripts/python.exe" not in text
