"""Generated CI references close through the adopter's own native owners."""

from __future__ import annotations

import difflib
import hashlib
from typing import TYPE_CHECKING

import pytest
import tomli_w
import yaml

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.contracts.gates import Gate
from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.declarations import retained_ci_steps
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source
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
@pytest.mark.parametrize("anchored", [False, True])
def test_every_gitlab_shell_list_is_observed(key: str, *, anchored: bool) -> None:
    """GitLab's native script-array anchors are commands, not unobserved list values."""
    pipeline = (
        f".setup: &setup [curl -fsS https://example.invalid]\nverify:\n  {key}: [*setup]\n"
        if anchored
        else f"verify:\n  {key}:\n    - curl -fsS https://example.invalid\n"
    )
    observed = product_references_from_files(
        {".gitlab-ci.yml": pipeline}, include_declarations=False
    )
    assert observed.references["executable"] == {"curl"}
    assert observed.unknown_paths == ()


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
            RepositoryProfileDeclaration(profile_id="adopter")
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


TEMPLATE = ".config/ci/templates/hosted/gitlab-ci.yml"
UNNAMED = ".config/ci/templates/hosted/release.yml"
PROJECTED = (
    'schema = "ethos-ci-template-consistency-v1"\n[[projection]]\n'
    f'template = "{TEMPLATE}"\nprojection = ".gitlab-ci.yml"\n'
)


@pytest.mark.parametrize(
    ("paths", "reason"),
    [
        ((TEMPLATE, ".gitlab-ci.yml"), "baseline_product_closure_matched"),
        (
            (TEMPLATE, ".gitlab-ci.yml", UNNAMED),
            "product_reference_not_admitted_at_baseline:executable:sha256sum",
        ),
    ],
    ids=["declared", "undeclared"],
)
def test_a_declared_template_belongs_to_its_pipelines_forge(
    tmp_path: Path, paths: tuple[str, ...], reason: str
) -> None:
    """A runner owns its identity in the declared template of its Forge's pipeline file only."""
    repo = tmp_path / "adopter"
    for directory in (".ethos", ".config/checks/ci-projection", ".config/ci/templates/hosted"):
        (repo / directory).mkdir(parents=True)
    git(repo, "init", "-b", "dev")
    files = {
        ".ethos/profile.toml": render_repository_profile(
            RepositoryProfileDeclaration(profile_id="adopter")
        ),
        ".ethos/release.toml": RELEASE,
        ".config/ci/runners.toml": RUNNERS,
        ".config/checks/ci-projection/policy.toml": PROJECTED,
        TEMPLATE: PIPELINE,
        ".gitlab-ci.yml": PIPELINE,
        UNNAMED: PIPELINE,
    }
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    after = PIPELINE + "    - sha256sum -c sums\n"
    patch = "".join(
        f"diff --git a/{path} b/{path}\n"
        + "".join(
            difflib.unified_diff(
                PIPELINE.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        for path in paths
    )

    report = patch_admission(root=repo, requested_paths=paths, baseline_head=baseline, patch=patch)

    assert report["reason"] == reason, report


@pytest.mark.parametrize("named", [True, False])
def test_the_semantic_closure_reads_the_same_template_forges(
    tmp_path: Path, *, named: bool
) -> None:
    """The repository closure owns a named template's runner identity and an unnamed one's not."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(tmp_path, ".config/ci/runners.toml", RUNNERS)
    for path in (TEMPLATE, ".gitlab-ci.yml"):
        write_reference_source(tmp_path, path, "verify:\n  script:\n    - sha256sum -c sums\n")
    if named:
        write_reference_source(tmp_path, ".config/checks/ci-projection/policy.toml", PROJECTED)

    gaps = repository_semantic_closure(tmp_path)["required_gaps"]

    assert isinstance(gaps, list)
    orphan = f"semantic_consumer_orphan:executable:sha256sum:{TEMPLATE},.gitlab-ci.yml"
    assert (orphan in gaps) is not named, gaps


GLUE = "$ErrorActionPreference = 'Stop'\nWrite-Host (Join-Path $env:CI_PROJECT_DIR 'mise')\n"
RECORD = ".config/ci/retained-steps.toml"
WINDOWS = yaml.safe_dump(
    {"native-windows": {"before_script": [GLUE], "script": ["git status"]}}, sort_keys=False
)
# `$ErrorActionPreference` is an expansion in command position, so it names no executable.
UNRETAINED = {"Join-Path", "Write-Host", "git"}


def _retention(text: str, jobs: tuple[str, ...] = ("native-windows",)) -> str:
    """Record one Windows glue step as the paradigm's retention record names it."""
    entry = {
        "file": ".gitlab-ci.yml",
        "jobs": list(jobs),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "class": "operating-system-glue",
        "owner": "fixture CI model",
        "reason": "The step runs before the locked toolchain exists.",
        "platforms": ["windows"],
        "evidence": "fixture",
    }
    return tomli_w.dumps({"step": [entry]})


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (_retention(GLUE), {"git"}),
        (_retention(GLUE, ("native-linux",)), UNRETAINED),
        (_retention(GLUE + "Write-Host done\n"), UNRETAINED),
        (_retention(GLUE).replace("windows", "plan9"), UNRETAINED),
    ],
    ids=["recorded", "other-job", "other-text", "incomplete"],
)
def test_recorded_glue_is_owned_by_its_retention_record(record: str, expected: set[str]) -> None:
    """A step the retention record binds by file, job and text is owned, not read as commands."""
    observed = product_references_from_files(
        {".gitlab-ci.yml": WINDOWS},
        include_declarations=False,
        retained_steps=retained_ci_steps({RECORD: record}),
    )
    assert observed.references["executable"] == expected


@pytest.mark.parametrize(
    ("edited", "reason"),
    [
        ("git status", "baseline_product_closure_matched"),
        (GLUE, "product_reference_not_admitted_at_baseline:executable:Join-Path"),
    ],
    ids=["native-step", "recorded-glue"],
)
def test_patch_admission_owns_glue_its_baseline_record_names(
    tmp_path: Path, edited: str, reason: str
) -> None:
    """Editing a recorded step leaves its record behind; editing beside it keeps the glue owned."""
    repo = tmp_path / "adopter"
    for directory in (".ethos", ".config/ci"):
        (repo / directory).mkdir(parents=True)
    git(repo, "init", "-b", "dev")
    files = {
        ".ethos/profile.toml": render_repository_profile(
            RepositoryProfileDeclaration(profile_id="adopter")
        ),
        ".ethos/release.toml": RELEASE,
        RECORD: _retention(GLUE),
        ".gitlab-ci.yml": WINDOWS,
    }
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    document = yaml.safe_load(WINDOWS)
    job = document["native-windows"]
    key = "before_script" if edited == GLUE else "script"
    job[key] = [job[key][0] + ("Write-Host done\n" if edited == GLUE else " --short")]
    after = yaml.safe_dump(document, sort_keys=False)
    patch = "diff --git a/.gitlab-ci.yml b/.gitlab-ci.yml\n" + "".join(
        difflib.unified_diff(
            WINDOWS.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/.gitlab-ci.yml",
            tofile="b/.gitlab-ci.yml",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(".gitlab-ci.yml",), baseline_head=baseline, patch=patch
    )

    assert report["reason"] == reason, report
