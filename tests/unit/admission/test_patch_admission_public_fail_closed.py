"""Reject unverifiable patch state and preserve exact source admission."""

from __future__ import annotations

import os
import tempfile
from functools import partial
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as admission
import ethos.adapters.process as process
from ethos.repository.policy.references.observation import deleted_input_gaps
from tests.support.governed_repository import active_change_repo
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path


_repository = partial(active_change_repo, files={"module.py": "VALUE = 1\n"})


def _patch(repo: Path, path: str = "module.py", content: str = "VALUE = 2\n") -> str:
    target = repo / path
    original = target.read_text(encoding="utf-8") if target.exists() else None
    target.write_text(content, encoding="utf-8")
    patch = git(repo, "diff", "--no-ext-diff", "--", path)
    if original is None:
        target.unlink()
    else:
        target.write_text(original, encoding="utf-8")
    return f"{patch}\n"


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("path-mismatch", "prewrite_patch_paths_mismatch"),
        ("baseline-missing", "prewrite_patch_baseline_missing"),
        ("preimage-mismatch", "prewrite_patch_preimage_mismatch"),
        ("binary", "prewrite_patch_binary_unsupported"),
        ("quoted-header", "prewrite_patch_invalid"),
        ("short-header", "prewrite_patch_invalid"),
        ("no-change", "prewrite_patch_invalid"),
    ],
)
def test_patch_admission_rejects_unverifiable_patch_state(
    tmp_path: Path, case: str, expected: str
) -> None:
    repo, head = _repository(tmp_path)
    patch = _patch(repo)
    requested = ("module.py",)
    if case == "path-mismatch":
        requested = ("new.py",)
    elif case == "baseline-missing":
        head = ""
    elif case == "preimage-mismatch":
        patch = patch.replace("VALUE = 1", "VALUE = 0")
    elif case == "binary":
        patch = "diff --git a/module.py b/module.py\nGIT binary patch\n"
    elif case == "quoted-header":
        patch = 'diff --git "a/module.py b/module.py\n'
    elif case == "short-header":
        patch = "diff --git a/module.py\n"
    elif case == "no-change":
        patch = "not a unified patch\n"

    report = admission.patch_admission(
        root=repo, requested_paths=requested, baseline_head=head, patch=patch
    )

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["reason"] == expected


def test_patch_admission_blocks_when_postimage_reference_observation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _repository(tmp_path)

    def unavailable(*_args: object, **_kwargs: object) -> dict[str, set[str]]:
        message = "reference observer unavailable"
        raise OSError(message)

    monkeypatch.setattr(admission, "product_references_from_files", unavailable)
    report = admission.patch_admission(
        root=repo, requested_paths=("module.py",), baseline_head=head, patch=_patch(repo)
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_postimage_failed"
    assert report["references"] == {}


def test_patch_admission_accepts_new_file_with_exact_preimage_and_reference_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native patch reaches Git as bytes, also where a text stream writes newlines as CRLF."""
    temporary = process.TemporaryFile
    crlf = {"newline": "\r\n"}
    monkeypatch.setattr(
        process,
        "TemporaryFile",
        lambda mode, encoding=None, **_named: temporary(
            mode, encoding=encoding, **(crlf if mode == "w+" else {})
        ),
    )
    repo = init_git_repo(tmp_path / "repo")
    commit_active_change(repo)
    head = git(repo, "rev-parse", "HEAD")
    path = "new.py"
    patch = (
        "diff --git a/new.py b/new.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/new.py\n"
        "@@ -0,0 +1 @@\n"
        "+VALUE = 1\n"
    )

    report = admission.patch_admission(
        root=repo, requested_paths=(path,), baseline_head=head, patch=patch
    )

    assert report["verdict"] == "pass"
    assert report["state"] == "admitted"


@pytest.mark.parametrize("name", ["build", f"build{os.pathsep}1"], ids=["plain", "separator"])
def test_patch_admission_reads_the_postimage_with_its_temporary_directory_in_a_work_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """Git skips a patch's paths in a plain directory inside another checkout.

    The verdict is the one from outside a checkout, also where the directory's name holds the
    separator of a path list, which defeats a ceiling on Git's discovery.
    """
    repo, _head = _repository(tmp_path)
    script = "tools/run.sh"
    (repo / script).parent.mkdir()
    (repo / script).write_text("echo start\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare a script")
    head = git(repo, "rev-parse", "HEAD")
    patch = _patch(repo, script, "echo start\nfrobnicate --now\n")
    checkout = init_git_repo(tmp_path / "other") / name
    checkout.mkdir()

    def admitted() -> dict[str, object]:
        return admission.patch_admission(
            root=repo, requested_paths=(script,), baseline_head=head, patch=patch
        )

    outside = admitted()
    monkeypatch.setattr(tempfile, "tempdir", str(checkout))
    inside = admitted()

    refused = "product_reference_not_admitted_at_baseline:executable:frobnicate"
    assert (outside["verdict"], outside["reason"]) == ("block", refused)
    assert (inside["verdict"], inside["reason"]) == ("block", refused)


@pytest.mark.parametrize("change", ["body", "new-command", "prefix", "delete-app", "retire"])
def test_patch_command_ownership_uses_exact_unchanged_context(tmp_path, change) -> None:
    """Changes retain imported namespaces but cannot inherit deleted or stale parents."""
    repo, _head = _repository(tmp_path)
    files = {
        "pyproject.toml": '[project]\nname="example"\nversion="1"\ndependencies=["cyclopts"]\n',
        "src/example/app.py": 'from cyclopts import App\napp = App(name="ethos")\n',
        "src/example/commands.py": (
            "from example.app import app as cli\n@cli.command\ndef status():\n    return 1\n"
        ),
    }
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare command context")
    head = git(repo, "rev-parse", "HEAD")
    handler = "src/example/commands.py"
    app = "src/example/app.py"
    target = repo / handler
    target.write_text(
        files[handler].replace(
            "status" if change == "new-command" else "return 1",
            "other" if change == "new-command" else "return 2",
        )
    )
    paths = (handler, app) if change in {"prefix", "delete-app", "retire"} else (handler,)
    if change == "prefix":
        (repo / app).write_text(files[app].replace("ethos", "different"))
    elif change in {"delete-app", "retire"}:
        (repo / app).unlink()
        if change == "retire":
            target.unlink()
    patch = git(repo, "diff", "--", *paths) + "\n"
    for relative in paths:
        (repo / relative).write_text(files[relative])
    report = admission.patch_admission(
        root=repo, requested_paths=paths, baseline_head=head, patch=patch
    )
    assert report["verdict"] == ("block" if change == "delete-app" else "pass")
    assert not report["references"].get("command")
    if change == "delete-app":
        assert report["reason"] == "deleted_input:src/example/app.py:src/example/commands.py:import"


@pytest.mark.parametrize(
    ("source", "path", "replacement", "expected"),
    [
        ("import pkg.owner as local", "consumer.py", False, "block"),
        ("from pkg import owner", "consumer.py", False, "block"),
        ("from .owner import item", "consumer.py", False, "block"),
        ("from . import owner", "consumer.py", False, "block"),
        ("from . import owner", "__init__.py", False, "block"),
        ("VALUE = 1", "consumer.py", False, "pass"),
        ("def invalid(:", "consumer.py", False, "unknown"),
        ("import pkg.owner", "consumer.py", True, "pass"),
    ],
)
def test_deleted_python_input_retains_import_identity(source, path, replacement, expected):
    files = {f"src/pkg/{path}": source}
    if replacement:
        files["src/pkg/owner/__init__.py"] = ""
    gaps, unknown = deleted_input_gaps(files, frozenset({"src/pkg/owner.py"}))
    assert bool(gaps) is (expected == "block")
    assert bool(unknown) is (expected == "unknown")


_OWNER_GAP = "deleted_input:src/pkg/owner.py:tests/test_owner.py:import"


@pytest.mark.parametrize(
    ("manifest", "expected"),
    [
        ('[project]\nname = "film"\ndependencies = ["Pkg>=1"]\n', "pass"),
        ('[project]\nname = "film"\n[project.optional-dependencies]\nrun = ["pkg"]\n', "pass"),
        ('[dependency-groups]\ntest = ["pkg"]\n', "pass"),
        ('[project]\nname = "pkg"\ndependencies = ["pkg"]\n', "block"),
        ('[project]\nname = "film"\ndependencies = ["pkg-tools"]\n', "block"),
        ('[build-system]\nrequires = ["pkg"]\n', "block"),
        ("[project\n", "block"),
    ],
    ids=["dependency", "optional", "group", "own-name", "other-name", "build-only", "malformed"],
)
def test_declared_dependency_replaces_a_deleted_package(manifest, expected):
    """A dependency of the same name serves imports of the vendored copy a patch deletes."""
    files = {"pyproject.toml": manifest, "tests/test_owner.py": "from pkg.owner import item\n"}
    gaps, _unknown = deleted_input_gaps(files, frozenset({"src/pkg/owner.py"}))
    assert gaps == ([] if expected == "pass" else [_OWNER_GAP])


@pytest.mark.parametrize(
    ("survivor", "expected"),
    [
        (None, ["deleted_input:.config/prettier:package.json:scripts.format"]),
        (".config/prettier/overrides.json", []),
    ],
    ids=["emptied", "kept"],
)
def test_a_script_input_naming_an_emptied_directory_is_a_deleted_input(survivor, expected):
    """A script that reads a directory whose every file a patch deletes has a dangling input."""
    files = {"package.json": '{"scripts": {"format": "prettier --config .config/prettier/ ."}}'}
    if survivor:
        files[survivor] = "{}\n"
    gaps, _unknown = deleted_input_gaps(files, frozenset({".config/prettier/base.json"}))
    assert gaps == expected


def test_the_source_of_a_move_is_a_path_of_the_request_and_a_deleted_input(tmp_path) -> None:
    """A move takes its source away: the request names it, and an import that stays dangles."""
    repo, _head = _repository(tmp_path)
    write_tree(
        repo,
        {
            "pyproject.toml": '[project]\nname="example"\nversion="1"\ndependencies=["cyclopts"]\n',
            "src/example/app.py": 'from cyclopts import App\napp = App(name="ethos")\n',
            "src/example/commands.py": "from example.app import app as cli\n",
        },
    )
    head = commit_fixture(repo, "declare an owner and its consumer")
    source, target = "src/example/app.py", "src/example/moved.py"
    patch = (
        f"diff --git a/{source} b/{target}\nsimilarity index 100%\n"
        f"rename from {source}\nrename to {target}\n"
    )

    def admitted(*requested: str) -> dict[str, object]:
        return admission.patch_admission(
            root=repo, requested_paths=requested, baseline_head=head, patch=patch
        )

    alone, both = admitted(target), admitted(source, target)
    assert (alone["verdict"], alone["reason"]) == ("block", "prewrite_patch_paths_mismatch")
    assert alone["paths"] == both["paths"] == [source, target]
    assert both["effects"] == {source: "delete", target: "create"}
    assert (both["verdict"], both["reason"]) == (
        "block",
        f"deleted_input:{source}:src/example/commands.py:import",
    )
