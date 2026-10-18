"""Repository orchestration runs through native commands and toolchain-owner tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.orchestration import ci_steps
from ethos.repository.paradigm.orchestration import inline_shell
from ethos.repository.paradigm.orchestration import orchestration_gaps

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "command",
    [
        "uv run --frozen python -m nox -s lint",
        "uv run nox -s tests -- --first \\\n  --second\n",
        'test "$QUALITY_RESULT" = success',
        "mise run check",
        "git checkout ${{ github.event.pull_request.head.sha || github.sha }}",
        "python -c 'import sys; sys.exit(0 if True else 1)'",
        "ethos prove --json > build/report.json 2>&1",
        "FOO=1 mise run check",
        "mise run check  # one task; no chaining && here",
        "find . -name '*.orig' -exec rm {} \\;",
    ],
)
def test_one_native_command_with_arguments_is_not_inline_shell(command: str) -> None:
    """Continued arguments, redirection, quoted text and Forge expressions are one command."""
    assert not inline_shell(command)


@pytest.mark.parametrize(
    "command",
    [
        "cd tools && make",
        "uv sync; npm ci",
        "npm ci || true",
        "git ls-files | wc -l",
        "if test -f x; then make; fi",
        "for name in a b; do echo $name; done",
        "while true\ndo sleep 1\ndone",
        "case $OS in linux) make ;; esac",
        "ethos prove --expect-head $(git rev-parse HEAD)",
        'echo "$(date)"',
        "echo `date`",
        "uv sync --locked\nnpm ci",
        "server & client",
    ],
)
def test_a_shell_program_in_one_step_is_inline_shell(command: str) -> None:
    """Chains, pipes, control flow, substitution, background jobs and several lines are programs."""
    assert inline_shell(command)


def test_ci_steps_read_every_gitlab_script_and_github_run() -> None:
    """Each script entry and run step is one step with a carrier naming its position."""
    gitlab = (
        "default:\n  before_script: [mise run bootstrap]\n"
        ".shared: &shared\n  - mise run check\n"
        "verify:\n  script:\n    - !reference [.shared]\n    - mise run fix\n"
        "  after_script: [echo done]\n"
        "variables:\n  FOO: bar\n"
    )
    assert ci_steps("gitlab", ".gitlab-ci.yml", gitlab) == [
        (".gitlab-ci.yml:default.before_script[0]", "mise run bootstrap"),
        (".gitlab-ci.yml:verify.script[1]", "mise run fix"),
        (".gitlab-ci.yml:verify.after_script[0]", "echo done"),
    ]
    github = (
        "on: push\njobs:\n  quality:\n    steps:\n      - uses: actions/checkout@v5\n"
        "      - run: mise run check\n      - name: Fix\n        run: mise run fix\n"
    )
    assert ci_steps("github", ".github/workflows/ci.yml", github) == [
        (".github/workflows/ci.yml:jobs.quality.steps[1]", "mise run check"),
        (".github/workflows/ci.yml:jobs.quality.steps[2]", "mise run fix"),
    ]
    assert ci_steps("gitlab", ".gitlab-ci.yml", "verify: [\n") == []
    assert ci_steps("forgejo", ".forgejo/workflows/ci.yml", github) == []


def _gaps(root: Path, files: dict[str, str]) -> list[tuple[str, str]]:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    gaps = orchestration_gaps(load_repository_paradigm(), root, frozenset(files))
    return [(gap.required_gap, gap.repair) for gap in gaps]


_PROFILE = 'profile_id = "sample"\n\n[proof]\ngate_registry = "system/gates.toml"\n'
_REGISTRY = (
    'schema_version = 1\nid = "sample"\n\n'
    '[proof_sets]\ndefault = ["secrets"]\nfull = ["secrets"]\n\n'
    '[[gates]]\nid = "secrets"\nkind = "security"\ncommand = {command}\n'
)


def test_a_gate_or_step_running_a_repository_script_is_shell_orchestration(
    tmp_path: Path,
) -> None:
    """The scenario's gate and CI step both name the script and their native repair."""
    script = "tools/ci/run-secrets-scan.sh"
    files = {
        script: "#!/bin/sh\ngitleaks dir .\n",
        ".ethos/profile.toml": _PROFILE,
        "system/gates.toml": _REGISTRY.format(command=f'["{script}"]'),
        ".gitlab-ci.yml": f"secrets:\n  script: [{script}]\n",
    }
    repair = f"replace {script} with a native command or toolchain-owner task"
    assert _gaps(tmp_path, files) == [
        ("repository_paradigm_shell_orchestration:.gitlab-ci.yml:secrets.script[0]", repair),
        ("repository_paradigm_shell_orchestration:system/gates.toml:gates.secrets", repair),
    ]


def test_a_ci_step_with_a_shell_program_is_inline_shell(tmp_path: Path) -> None:
    """The scenario's conditional names the step and the task that replaces it."""
    files = {
        ".github/workflows/ci.yml": (
            "on: push\njobs:\n  quality:\n    steps:\n"
            "      - run: if test -f x; then mise run check; fi\n"
        )
    }
    assert _gaps(tmp_path, files) == [
        (
            "repository_paradigm_inline_shell:.github/workflows/ci.yml:jobs.quality.steps[0]",
            (
                "make the step invoke one native command or toolchain-owner task; move a sequence "
                "into a task, environment into the Forge's variables and a directory change into "
                "its working-directory key"
            ),
        )
    ]


def test_a_gate_that_runs_a_shell_program_is_inline_shell(tmp_path: Path) -> None:
    """A gate that hands a program to a shell interpreter embeds orchestration too."""
    files = {
        ".ethos/profile.toml": _PROFILE,
        "system/gates.toml": _REGISTRY.format(command='["bash", "-c", "gitleaks dir ."]'),
    }
    [(gap, _repair)] = _gaps(tmp_path, files)
    assert gap == "repository_paradigm_inline_shell:system/gates.toml:gates.secrets"


def test_a_profile_gate_that_runs_a_shell_program_is_inline_shell(tmp_path: Path) -> None:
    """Gates declared in the profile itself are judged like registry gates."""
    gates = "".join(
        f'[[proof.gates]]\nid = "{name}"\nkind = "{kind}"\ncommand = {command}\n'
        f'dimensions = {dimensions}\nexecution_mode = "subprocess"\nevidence_class = "{evidence}"\n'
        'trust_bearing = true\ntool_adapter = "repository-native"\n\n'
        for name, kind, command, dimensions, evidence in (
            (
                "sample-tests",
                "test",
                '["bash", "-c", "pytest && ruff check ."]',
                '["test"]',
                "proof",
            ),
            ("sample-static", "typing", '["ty", "check"]', '["static-analysis"]', "contract"),
        )
    )
    profile = (
        'profile_id = "sample"\n\n[proof]\n'
        'code_correctness_gates = ["sample-tests", "sample-static"]\n\n'
        '[proof.code_correctness_map]\nbehavior = "sample-tests"\n'
        f'static-analysis = "sample-static"\n\n{gates}'
    )
    [(gap, _repair)] = _gaps(tmp_path, {".ethos/profile.toml": profile})
    assert gap == "repository_paradigm_inline_shell:.ethos/profile.toml:proof.gates.sample-tests"


@pytest.mark.parametrize("registry", [None, "schema_version = [\n"])
def test_an_absent_or_unreadable_gate_registry_is_left_to_its_owner(
    tmp_path: Path, registry: str | None
) -> None:
    """Only a readable gate registry contributes gate commands; its owner reports the rest."""
    files = {".ethos/profile.toml": _PROFILE}
    if registry is not None:
        files["system/gates.toml"] = registry
    assert _gaps(tmp_path, files) == []


def test_native_gates_and_steps_conform(tmp_path: Path) -> None:
    """Native commands and owner tasks, in gates and in both Forges, need no repair."""
    files = {
        ".ethos/profile.toml": _PROFILE,
        "system/gates.toml": _REGISTRY.format(command='["mise", "run", "secrets"]'),
        ".gitlab-ci.yml": "secrets:\n  script: [mise run secrets]\n",
        ".github/workflows/ci.yml": (
            "on: push\njobs:\n  a:\n    steps:\n      - run: mise run check\n"
        ),
    }
    assert _gaps(tmp_path, files) == []
