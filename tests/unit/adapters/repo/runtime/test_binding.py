"""Runtime admission follows selected execution and actual schema provenance."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.runtime.authority as authority
import ethos.adapters.repo.runtime.binding as binding
import ethos.repository.policy.schema as schemas
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import current_runtime
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
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
