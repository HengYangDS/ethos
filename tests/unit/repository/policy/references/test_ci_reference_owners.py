"""Generated CI references close through the adopter's own native owners."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.contracts.gates import Gate
from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

GATE = ("mise", "exec", "--locked", "--", "uv", "run", "--locked", "nox", "-s", "quality")
RELEASE = (
    '[[publication.peers]]\nid = "gitlab"\nprovider = "gitlab"\n'
    'role = "organization_collaboration"\ngit_remote = "gitlab"\ncapabilities = ["repository"]\n'
)
CI = "verify:\n  script:\n    - git fetch gitlab dev\n    - " + " ".join(GATE) + "\n"


def test_mise_exec_runs_its_command_after_the_separator() -> None:
    """Mise is a wrapper like uv run: the declared command after `--` is what runs."""
    assert command_executables(GATE, {}) == {"mise", "uv", "nox"}
    assert command_executables(("mise", "exec", "python@3.14"), {}) == {"mise"}


@pytest.mark.parametrize(
    ("added", "reason"),
    [
        ("ethos status --json", "baseline_product_closure_matched"),
        (
            "curl -fsS https://example.invalid",
            "product_reference_not_admitted_at_baseline:executable:curl",
        ),
    ],
)
def test_generated_ci_closes_through_product_publication_and_gate_owners(
    tmp_path: Path, added: str, reason: str
) -> None:
    """Product runtime, publication peers and declared gate wrappers own CI references."""
    repo = tmp_path / "adopter"
    (repo / ".ethos").mkdir(parents=True)
    git(repo, "init", "-b", "dev")
    profile = RepositoryProfileDeclaration(
        profile_id="adopter",
        proof=ProofPolicy(
            code_correctness_gates=("quality",),
            code_correctness_map={"behavior": "quality", "static-analysis": "quality"},
            gates=(Gate(id="quality", kind="test", command=GATE),),
        ),
    )
    files = {
        ".ethos/profile.toml": render_repository_profile(profile),
        ".ethos/release.toml": RELEASE,
        ".gitlab-ci.yml": CI,
    }
    for path, text in files.items():
        (repo / path).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    after = f"{CI}    - {added}\n"
    patch = "diff --git a/.gitlab-ci.yml b/.gitlab-ci.yml\n" + "".join(
        difflib.unified_diff(
            CI.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/.gitlab-ci.yml",
            tofile="b/.gitlab-ci.yml",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(".gitlab-ci.yml",), baseline_head=baseline, patch=patch
    )

    assert report["reason"] == reason, report


@pytest.mark.parametrize("requires", ['requires-python = ">=3.12"\n', ""])
def test_python_project_declares_its_interpreter(requires: str) -> None:
    """As devEngines declares npm, a project's requires-python declares the interpreter it runs."""
    text = f'[project]\nname = "adopter"\n{requires}'
    owned = native_owned_references_from_files({"pyproject.toml": text})["executable"]
    assert ("python" in owned) is bool(requires)


@pytest.mark.parametrize("key", ["script", "before_script", "after_script"])
def test_every_gitlab_shell_list_is_observed(key: str) -> None:
    """GitLab runs before_script and after_script like script, so their commands are references."""
    pipeline = f"verify:\n  {key}:\n    - curl -fsS https://example.invalid\n"
    observed = product_references_from_files(
        {".gitlab-ci.yml": pipeline}, include_declarations=False
    )
    assert observed.references["executable"] == {"curl"}


def test_forge_expressions_are_values_not_commands() -> None:
    """A Forge expression is resolved before the shell runs, so it never names a command."""
    workflow = (
        "jobs:\n  verify:\n    steps:\n"
        "      - run: \"git status --short=${{ inputs.a && inputs.b == '' }}\"\n"
    )
    observed = product_references_from_files(
        {".github/workflows/verify.yml": workflow}, include_declarations=False
    )
    assert observed.references["executable"] == {"git"}


RUNNERS = '[[runner]]\nforge = "gitlab"\nexecutables = ["sha256sum"]\n'
WORKFLOW = "jobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n      - run: git status\n"
PIPELINE = "verify:\n  before_script:\n    - git fetch gitlab dev\n  script:\n    - git status\n"


@pytest.mark.parametrize(
    ("runners", "path", "added", "reason"),
    [
        (
            RUNNERS,
            ".gitlab-ci.yml",
            "    - sha256sum -c sums\n",
            "baseline_product_closure_matched",
        ),
        (
            RUNNERS,
            ".github/workflows/verify.yml",
            "      - run: sha256sum -c sums\n",
            "product_reference_not_admitted_at_baseline:executable:sha256sum",
        ),
        (
            RUNNERS,
            ".gitlab-ci.yml",
            "    - curl -fsS https://example.invalid\n",
            "product_reference_not_admitted_at_baseline:executable:curl",
        ),
        (
            RUNNERS.replace("executables", "executable"),
            ".gitlab-ci.yml",
            "    - sha256sum -c sums\n",
            "product_reference_not_admitted_at_baseline:executable:sha256sum",
        ),
    ],
    ids=["declared", "other-forge", "undeclared", "malformed"],
)
def test_declared_runners_own_only_their_forge_pipelines(
    tmp_path: Path, runners: str, path: str, added: str, reason: str
) -> None:
    """A forge's declared runner commands close its own pipelines and nothing else."""
    repo = tmp_path / "adopter"
    for directory in (".ethos", ".config/ci", ".github/workflows"):
        (repo / directory).mkdir(parents=True)
    git(repo, "init", "-b", "dev")
    files = {
        ".ethos/profile.toml": render_repository_profile(
            RepositoryProfileDeclaration.bootstrap("adopter")
        ),
        ".ethos/release.toml": RELEASE,
        ".config/ci/runners.toml": runners,
        ".gitlab-ci.yml": PIPELINE,
        ".github/workflows/verify.yml": WORKFLOW,
    }
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    before = files[path]
    patch = f"diff --git a/{path} b/{path}\n" + "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            (before + added).splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(path,), baseline_head=baseline, patch=patch
    )

    assert report["reason"] == reason, report
