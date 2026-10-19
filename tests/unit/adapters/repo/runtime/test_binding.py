"""Runtime admission follows selected execution and actual schema provenance."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.runtime.authority as authority
import ethos.adapters.repo.runtime.binding as binding
import ethos.adapters.repo.runtime.selection as runtime_selection
import ethos.cli as cli
import ethos.repository.policy.schema as schemas
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import current_runtime
from tests.support.ethos_cli_runner import result_data
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import start_adopted_candidate
from tests.support.runtime_scenarios import install_fixture_hook_runtime


def test_selected_runtime_provenance_does_not_replace_incumbent_hooks(tmp_path: Path) -> None:
    """A selected package can own execution without claiming hook enforcement."""
    root = init_git_repo(tmp_path / "repo")
    install_fixture_hook_runtime(root)
    git(root, "config", "--worktree", "core.hooksPath", ".incumbent-hooks")
    selected = current_runtime(Path(git_common_dir(root)))
    original = binding.hook_runtime_binding(root)
    report = binding.runtime_binding(root, selected_runtime=selected)

    assert binding.runtime_binding_check({"runtime_binding": report})["verdict"] == "pass", report
    assert original["required_gaps"]
    assert binding.hook_runtime_binding(root)["required_gaps"] == original["required_gaps"]
    assert git(root, "config", "core.hooksPath") == ".incumbent-hooks"


@pytest.mark.parametrize("foreign_member", [None, "package", "schema", "python"])
def test_runtime_selection_requires_exact_native_package_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_member: str | None
) -> None:
    """Containment alone cannot certify an unrelated package, schema tree or interpreter."""
    root = init_git_repo(tmp_path / "repo")
    install_fixture_hook_runtime(root)
    selected = current_runtime(Path(git_common_dir(root)))
    version = ".".join(selected.python_version.split(".")[:2])
    site = (
        selected.root
        / "python"
        / (
            "Lib/site-packages"
            if selected.platform == "windows"
            else f"lib/python{version}/site-packages"
        )
    )
    package = site / "ethos"
    schema = package / "resources/system/schemas"
    module = package / "__init__.py"
    python = selected.python
    if foreign_member == "package":
        module = selected.root / "unrelated/ethos/__init__.py"
    if foreign_member == "schema":
        schema = selected.root / "unrelated/system/schemas"
    if foreign_member == "python":
        python = selected.root / "unrelated/bin/python"
    monkeypatch.setattr(binding, "ethos", SimpleNamespace(__file__=module))
    monkeypatch.setattr(binding, "sys", SimpleNamespace(executable=python))
    monkeypatch.setattr(binding, "schema_source_root", lambda: schema)
    monkeypatch.setattr(binding, "runner_source_root", lambda _module: module.parent)
    monkeypatch.setattr(binding, "invoking_build_identity", lambda: selected.build)
    hook = {"required_gaps": ["incumbent_hooks_not_replaced"], "python": ""}

    report = binding.runtime_binding(root, hook_binding=hook)

    assert binding.runtime_binding_check({"runtime_binding": report})["verdict"] == (
        "pass" if foreign_member is None else "block"
    ), report


@pytest.mark.parametrize("registry", [False, True])
def test_selected_package_admits_without_adopter_schemas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, registry: bool
) -> None:
    """Storage representation cannot reject the adopter's exact package runtime."""
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "node-repository"\n'
        + ('[proof]\ngate_registry = ".config/gates.toml"\n' if registry else ""),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        binding,
        "hook_runtime_binding",
        lambda _root, **_kwargs: {"required_gaps": [], "python": sys.executable},
    )
    report = binding.runtime_binding(tmp_path)
    assert report["state"] == "bound_to_common_runtime"
    assert report["schema_matches_audit_root"] is False
    assert binding.runtime_binding_check({"runtime_binding": report})["verdict"] == "pass"


def test_adopter_filename_does_not_change_schema_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Diagnostics agree with load_schema instead of trusting a lookalike path."""
    impostor = tmp_path / "system/schemas/kernel/workspace-status.schema.json"
    impostor.parent.mkdir(parents=True)
    impostor.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        binding,
        "hook_runtime_binding",
        lambda _root, **_kwargs: {"required_gaps": ["runtime_missing"], "python": ""},
    )
    report = binding.runtime_binding(tmp_path)
    assert report["schema_source_root"] != str(tmp_path)
    assert report["schema_matches_audit_root"] is False
    assert schemas.load_schema("workspace-status.schema.json", root=tmp_path) != {}


def test_unbound_external_runner_is_rejected_independent_of_storage(tmp_path: Path) -> None:
    """A valid profile is not proof of selected execution authority."""
    report = binding.runtime_binding_check(
        {
            "runtime_binding": {
                "audit_root": str(tmp_path),
                "runner_source_root": "/foreign/runtime",
                "schema_source_root": "/foreign/runtime",
                "runner_matches_audit_root": False,
                "schema_matches_audit_root": False,
                "state": "external_current_runner",
            }
        }
    )
    assert report["verdict"] == "block"
    assert report["reason"] == "root_binding_mismatch"


@pytest.mark.parametrize("supplied_hook", [False, True])
def test_source_runner_matching_selected_build_remains_usable(tmp_path, monkeypatch, supplied_hook):
    """A source runner with exact selected build identity supports native fixtures."""
    root = init_git_repo(tmp_path / "repo")
    install_fixture_hook_runtime(root)
    observed = Mock(wraps=authority.runtime_build_identity)
    monkeypatch.setattr(authority, "runtime_build_identity", observed)
    hook = binding.hook_runtime_binding(root) if supplied_hook else None
    report = binding.runtime_binding(root, hook_binding=hook)
    assert binding.runtime_binding_check({"runtime_binding": report})["verdict"] == "pass", report
    observed.assert_called_once()
    binding.runtime_binding(root)
    assert observed.call_count == 2  # A separate observation cannot reuse the earlier source.


@pytest.mark.parametrize("origin", ["accepted", "supplied", "foreign"])
def test_equal_expected_build_does_not_establish_invoking_source(tmp_path, monkeypatch, origin):
    """An accepted build or a different source cannot certify this runner's overlay."""
    root = init_git_repo(tmp_path / "repo")
    install_fixture_hook_runtime(root)
    selected = authority.invoking_build_identity()
    source = Path(authority.__file__).resolve().parents[5]
    monkeypatch.setattr(
        authority, "expected_runtime_build", lambda _root: authority.RuntimeBuild(selected, source)
    )
    hook = binding.hook_runtime_binding(
        root, expected_build=selected if origin == "supplied" else None
    )
    assert "invoking_source_root" not in hook
    if origin == "foreign":
        hook["invoking_source_root"] = str(tmp_path / "another-source")
    observed = Mock(return_value=selected._replace(source_tree="a" * 40))
    monkeypatch.setattr(binding, "invoking_build_identity", observed)
    report = binding.runtime_binding(root, hook_binding=hook)
    observed.assert_called_once()
    assert binding.runtime_binding_check({"runtime_binding": report})["verdict"] == "block"


def test_missing_runtime_observation_remains_unknown() -> None:
    """A missing observation is neither matched nor an ordinary mismatch."""
    assert binding.runtime_binding_check({}) == {
        "verdict": "unknown",
        "reason": "runtime_binding_unavailable",
    }


def test_self_console_validates_runtime_once_and_rereads_on_the_next_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A status command must not hash one selected image twice or retain it for the next call."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    selected = current_runtime(Path(git_common_dir(repo)))
    inventory = runtime_selection.runtime_file_inventory
    reads: list[Path] = []

    def observe(runtime: Path):
        reads.append(runtime)
        return inventory(runtime)

    monkeypatch.setattr(runtime_selection, "runtime_file_inventory", observe)
    monkeypatch.setattr(cli.sys, "executable", selected.python.as_posix())
    monkeypatch.setattr(cli.sys, "argv", ["ethos", "status", "--root", repo.as_posix(), "--json"])

    with pytest.raises(SystemExit) as completed:
        cli.console_main()

    assert completed.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "pass", payload["required_gaps"]
    assert result_data(payload)["hook_runtime"]["current"] is True
    assert reads == [selected.root]

    declaration = next(selected.root.glob("python/**/ethos/adapters/repo/hook/binding.toml"))
    declaration.chmod(0o644)
    declaration.write_bytes(declaration.read_bytes() + b"\n")
    independent = hook_runtime_binding(repo)
    assert independent["current"] is False
    assert (
        "write_admission_not_armed:runtime_schema_migration_required"
        in independent["required_gaps"]
    )

    with pytest.raises(SystemExit) as refused:
        cli.console_main()

    assert refused.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["hook_runtime_manifest_invalid"]
    assert reads == [selected.root, selected.root, selected.root]


@pytest.mark.parametrize("replacement", ["changed", "symlinked"])
def test_self_console_rereads_current_before_reporting_hook_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replacement: str,
) -> None:
    """A selector changed after routing cannot borrow the routed image's hook readiness."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    common = Path(git_common_dir(repo))
    selected = current_runtime(common)
    selector = common / "ethos/runtime/CURRENT"
    main = cli.main

    def inspect_changed_selection() -> None:
        if replacement == "changed":
            selector.write_text("a" * 64 + "\n", encoding="utf-8")
        else:
            redirected = selector.parent / "peer-selector"
            redirected.write_bytes(selector.read_bytes())
            selector.unlink()
            selector.symlink_to(redirected)
        main()

    monkeypatch.setattr(cli.sys, "executable", selected.python.as_posix())
    monkeypatch.setattr(cli.sys, "argv", ["ethos", "status", "--root", repo.as_posix(), "--json"])
    monkeypatch.setattr(cli, "main", inspect_changed_selection)

    with pytest.raises(SystemExit) as completed:
        cli.console_main()

    assert completed.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    runtime = result_data(payload)["hook_runtime"]
    assert payload["verdict"] == "block"
    assert runtime["current"] is False
    assert runtime["runtime_digest"] == ""
    assert "write_admission_not_armed:runtime_manifest" in payload["required_gaps"]


def test_status_runtime_observation_is_repository_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Inspecting a second repository validates its own runtime, not the routed image."""
    repo, _candidate = start_adopted_candidate(tmp_path / "local")
    other, _other_candidate = start_adopted_candidate(tmp_path / "other")
    selected = current_runtime(Path(git_common_dir(repo)))
    other_selected = current_runtime(Path(git_common_dir(other)))
    inventory = runtime_selection.runtime_file_inventory
    reads: list[Path] = []
    observations = []
    main = cli.main

    def observe(runtime: Path):
        reads.append(runtime)
        return inventory(runtime)

    def inspect_other_repository() -> None:
        observations.append(hook_runtime_binding(other))
        main()

    monkeypatch.setattr(runtime_selection, "runtime_file_inventory", observe)
    monkeypatch.setattr(cli.sys, "executable", selected.python.as_posix())
    monkeypatch.setattr(cli.sys, "argv", ["ethos", "status", "--root", repo.as_posix(), "--json"])
    monkeypatch.setattr(cli, "main", inspect_other_repository)

    with pytest.raises(SystemExit) as completed:
        cli.console_main()

    assert completed.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "pass", payload["required_gaps"]
    assert observations[0]["current"] is True
    assert observations[0]["runtime_digest"] == other_selected.digest
    assert reads == [selected.root, other_selected.root]


def test_prewrite_console_validates_runtime_independently_of_routing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Write admission keeps its own fresh payload validation after console routing."""
    fixture = prepared_work_lane(tmp_path)
    selected = current_runtime(Path(git_common_dir(fixture.worktree)))
    inventory = runtime_selection.runtime_file_inventory
    reads: list[Path] = []

    def observe(runtime: Path):
        reads.append(runtime)
        return inventory(runtime)

    monkeypatch.setattr(runtime_selection, "runtime_file_inventory", observe)
    monkeypatch.setattr(cli.sys, "executable", selected.python.as_posix())
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setattr(
        cli.sys,
        "argv",
        [
            "ethos",
            "lane",
            "prewrite",
            "README.md",
            "--root",
            fixture.worktree.as_posix(),
            "--editor-root",
            fixture.worktree.as_posix(),
            "--require-editor-root",
            "--json",
        ],
    )

    with pytest.raises(SystemExit) as completed:
        cli.console_main()

    assert completed.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "pass", payload["required_gaps"]
    assert reads == [selected.root, selected.root]
