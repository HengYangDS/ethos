"""Native package-manager declarations bind immutable public patch admission."""

from __future__ import annotations

import difflib
import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.manifests import NodeManifest
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path


NPM_ENGINE = {"name": "npm", "version": "12.2.0", "onFail": "error"}


@pytest.mark.parametrize(
    "manager",
    [NPM_ENGINE, [NPM_ENGINE], {"name": "npm"}, {**NPM_ENGINE, "onFail": "warn"}],
)
def test_native_package_manager_declares_npm_without_duplicate(manager: object) -> None:
    text = json.dumps({"devEngines": {"packageManager": manager}})
    manifest = NodeManifest.read(text)

    assert manifest is not None
    assert native_owned_references_from_files({"package.json": text})["executable"] == {"npm"}
    assert reference_consumer_sources_from_files({"package.json": text}).unknown_paths == ()


@pytest.mark.parametrize(
    "payload",
    [{}, {"devEngines": {}}, {"devEngines": {"packageManager": []}}],
)
def test_absent_native_package_manager_remains_undeclared(payload: dict[str, object]) -> None:
    text = json.dumps(payload)

    assert NodeManifest.read(text) is not None
    assert native_owned_references_from_files({"package.json": text})["executable"] == set()
    assert reference_consumer_sources_from_files({"package.json": text}).unknown_paths == ()


@pytest.mark.parametrize(
    "engines",
    [
        None,
        [],
        {"packageManager": None},
        {"packageManager": "npm"},
        {"packageManager": {}},
        {"packageManager": {"name": 12}},
        {"packageManager": {"name": ""}},
        {"packageManager": {**NPM_ENGINE, "version": 12}},
        {"packageManager": {**NPM_ENGINE, "version": None}},
        {"packageManager": {**NPM_ENGINE, "onFail": "allow"}},
        {"packageManager": {**NPM_ENGINE, "onFail": None}},
        {"packageManager": {**NPM_ENGINE, "unexpected": True}},
        {"packageManager": [NPM_ENGINE, {"name": 12}]},
        {"packageManager": [[NPM_ENGINE]]},
    ],
)
def test_invalid_native_package_manager_preserves_unknown_carrier(engines: object) -> None:
    text = json.dumps({"devEngines": engines})

    assert NodeManifest.read(text) is None
    assert native_owned_references_from_files({"package.json": text})["executable"] == set()
    assert reference_consumer_sources_from_files({"package.json": text}).unknown_paths == (
        "package.json",
    )


def test_native_package_manager_alternatives_and_legacy_declaration() -> None:
    text = json.dumps(
        {
            "packageManager": "yarn@4.0.0",
            "devEngines": {
                "runtime": {"name": "node"},
                "packageManager": [NPM_ENGINE, {"name": "pnpm", "onFail": "ignore"}],
            },
        }
    )

    assert native_owned_references_from_files({"package.json": text})["executable"] == {
        "npm",
        "pnpm",
        "yarn",
    }


def test_valid_repository_binding_inherits_product_console_ownership() -> None:
    """Governed content consumes the product's console without a duplicate package."""
    profile = render_repository_profile(RepositoryProfileDeclaration.bootstrap("native-docs"))

    owned = native_owned_references_from_files({".ethos/profile.toml": profile})

    assert owned["executable"] == {"ethos"}
    assert owned["distribution"] == set()
    assert owned["import"] == set()


@pytest.mark.parametrize(
    ("binding", "verdict"),
    [
        ('profile_id = "native-docs"\n', "pass"),
        (None, "block"),
        ('profile_id = ""\n', "block"),
        ("[profile", "block"),
    ],
    ids=("governed", "unadopted", "invalid", "malformed"),
)
def test_product_console_patch_admission_uses_immutable_governed_binding(
    tmp_path: Path, binding: str | None, verdict: str
) -> None:
    """A mutable binding cannot grant or withdraw the product's baseline ownership."""
    repo = tmp_path / "governed-content"
    repo.mkdir()
    git(repo, "init", "-b", "dev")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    if binding is not None:
        profile.write_text(binding, encoding="utf-8")
    path = "docs/README.md"
    document = repo / path
    document.parent.mkdir()
    before = "# Product entry\n\n```console\n$ ethos --help\n```\n"
    after = "# Product entry\n\n```console\n$ ethos --version\n```\n"
    document.write_text(before, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    poisoned = "" if verdict == "pass" else 'profile_id = "native-docs"\n'
    profile.write_text(poisoned, encoding="utf-8")
    patch = f"diff --git a/{path} b/{path}\n" + "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(path,), baseline_head=baseline, patch=patch
    )

    assert report["references"] == {"executable": ["ethos"]}
    assert report["verdict"] == verdict, report
    assert report["reason"] == (
        "baseline_product_closure_matched"
        if verdict == "pass"
        else "product_reference_not_admitted_at_baseline:executable:ethos"
    )
    assert document.read_text(encoding="utf-8") == before
    assert profile.read_text(encoding="utf-8") == poisoned


@pytest.mark.parametrize("manager", [NPM_ENGINE, [NPM_ENGINE], None])
@pytest.mark.parametrize("path", ["pipelines/verify.yml", "automation/npm-check.yaml"])
def test_public_patch_admission_uses_immutable_native_declaration(
    tmp_path: Path, manager: object, path: str
) -> None:
    """A surviving CI consumer closes only against its immutable declared baseline."""
    repo = tmp_path / "native-source"
    repo.mkdir()
    git(repo, "init", "-b", "dev")
    payload = {} if manager is None else {"devEngines": {"packageManager": manager}}
    package = repo / "package.json"
    source = json.dumps(payload) + "\n"
    package.write_text(source, encoding="utf-8")
    workflow = repo / path
    workflow.parent.mkdir(parents=True)
    before = "jobs:\n  verify:\n    script: npm ci\n"
    after = "jobs:\n  verify:\n    script: npm ci --ignore-scripts\n"
    workflow.write_text(before, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    # Poison the mutable declaration: only the immutable Git tree may authorize npm.
    package.write_text(
        "{}\n"
        if manager is not None
        else json.dumps({"devEngines": {"packageManager": NPM_ENGINE}}) + "\n",
        encoding="utf-8",
    )
    patch = f"diff --git a/{path} b/{path}\n" + "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(path,), baseline_head=baseline, patch=patch
    )

    references = report["references"]
    assert isinstance(references, dict)
    assert references["executable"] == ["npm"]
    if manager is None:
        assert report["verdict"] == "block", report
        assert report["reason"] == "product_reference_not_admitted_at_baseline:executable:npm"
    else:
        assert report["verdict"] == "pass", report
        assert report["reason"] == "baseline_product_closure_matched"
    assert report["reference_coverage"] == "evaluated"
    assert git(repo, "show", f"{baseline}:package.json") == source.strip()
    assert workflow.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    "manager", [{**NPM_ENGINE, "version": 12}, {**NPM_ENGINE, "onFail": "allow"}]
)
def test_public_patch_admission_reports_invalid_native_declaration(
    tmp_path: Path, manager: object
) -> None:
    """An invalid postimage remains an unknown carrier, never a silent declaration."""
    repo = tmp_path / "native-invalid"
    repo.mkdir()
    git(repo, "init", "-b", "dev")
    before = json.dumps({"devEngines": {"packageManager": NPM_ENGINE}}) + "\n"
    after = json.dumps({"devEngines": {"packageManager": manager}}) + "\n"
    package = repo / "package.json"
    package.write_text(before, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    patch = "diff --git a/package.json b/package.json\n" + "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/package.json",
            tofile="b/package.json",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=("package.json",), baseline_head=baseline, patch=patch
    )

    assert report["verdict"] == "unknown", report
    assert report["reason"] == "reference_carrier_unknown:package.json"
    assert report["reference_coverage"] == "unknown"
    assert package.read_text(encoding="utf-8") == before
