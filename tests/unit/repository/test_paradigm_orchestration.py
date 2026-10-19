"""Repository orchestration runs through native commands and toolchain-owner tasks."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.orchestration import CiStep
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
    """Each script entry and run step is one step with its job and a carrier naming its position."""
    gitlab = (
        "default:\n  before_script: [mise run bootstrap]\n"
        ".shared: &shared\n  - mise run check\n"
        "verify:\n  script:\n    - !reference [.shared]\n    - mise run fix\n"
        "  after_script: [echo done]\n"
        "variables:\n  FOO: bar\n"
    )
    assert ci_steps("gitlab", ".gitlab-ci.yml", gitlab) == [
        CiStep(".gitlab-ci.yml:default.before_script[0]", "default", "mise run bootstrap"),
        CiStep(".gitlab-ci.yml:verify.script[1]", "verify", "mise run fix"),
        CiStep(".gitlab-ci.yml:verify.after_script[0]", "verify", "echo done"),
    ]
    github = (
        "on: push\njobs:\n  quality:\n    steps:\n      - uses: actions/checkout@v5\n"
        "      - run: mise run check\n      - name: Fix\n        run: mise run fix\n"
    )
    assert ci_steps("github", ".github/workflows/ci.yml", github) == [
        CiStep(
            ".github/workflows/ci.yml:jobs.quality.steps[1]",
            "quality",
            "mise run check",
        ),
        CiStep(".github/workflows/ci.yml:jobs.quality.steps[2]", "quality", "mise run fix"),
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
        (
            "repository_paradigm_shell_orchestration:.gitlab-ci.yml:secrets.script[0]",
            repair,
        ),
        (
            "repository_paradigm_shell_orchestration:system/gates.toml:gates.secrets",
            repair,
        ),
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
                "its working-directory key; record only an official installer or necessary "
                "operating-system glue in .config/ci/retained-steps.toml"
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


def test_a_profile_gate_that_runs_a_shell_program_is_inline_shell(
    tmp_path: Path,
) -> None:
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
            (
                "sample-static",
                "typing",
                '["ty", "check"]',
                '["static-analysis"]',
                "contract",
            ),
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


_RECORD = ".config/ci/retained-steps.toml"
_GLUE = "Set-Location $env:CI_PROJECT_DIR\ngit config --system core.longpaths true\n"
_GLUE_STEP = (
    f"windows:\n  script:\n    - |\n      {_GLUE.replace(chr(10), chr(10) + '      ').rstrip()}\n"
)


def _record(command: str, **fields: object) -> str:
    """Return one `[[step]]` entry that retains a command, with fields overridden or dropped."""
    entry: dict[str, object] = {
        "file": ".gitlab-ci.yml",
        "jobs": ["windows"],
        "sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
        "class": "operating-system-glue",
        "owner": "CI pipeline model",
        "reason": "Git needs long paths before the checkout that every native command follows.",
        "platforms": ["windows"],
        "evidence": "GitLab job 55210 ran it on ci-windows-arm64-shell",
    }
    entry.update(fields)
    lines = [f"{key} = {json.dumps(value)}" for key, value in entry.items() if value is not None]
    return "[[step]]\n" + "\n".join(lines) + "\n"


def _identities(root: Path, files: dict[str, str]) -> list[str]:
    return sorted(gap for gap, _repair in _gaps(root, files))


def test_recorded_glue_in_a_ci_step_conforms(tmp_path: Path) -> None:
    """The scenario's complete record names the step's file, job and exact text digest."""
    files = {".gitlab-ci.yml": _GLUE_STEP, _RECORD: _record(_GLUE)}
    assert _gaps(tmp_path, files) == []


def test_recorded_glue_survives_another_yaml_quoting(tmp_path: Path) -> None:
    """The digest covers the parsed step text, so a quoted scalar keeps the record current."""
    quoted = f"windows:\n  script:\n    - {json.dumps(_GLUE)}\n"
    files = {".gitlab-ci.yml": quoted, _RECORD: _record(_GLUE)}
    assert _gaps(tmp_path, files) == []


def test_edited_glue_reports_the_step_and_the_stale_record(tmp_path: Path) -> None:
    """Changing what runs re-reports the inline shell and leaves the record matching nothing."""
    edited = _GLUE_STEP.replace("--system", "--global")
    files = {".gitlab-ci.yml": edited, _RECORD: _record(_GLUE)}
    assert _gaps(tmp_path, files) == [
        (
            "repository_paradigm_inline_shell:.gitlab-ci.yml:windows.script[0]",
            (
                "make the step invoke one native command or toolchain-owner task; move a sequence "
                "into a task, environment into the Forge's variables and a directory change into "
                "its working-directory key; record only an official installer or necessary "
                "operating-system glue in .config/ci/retained-steps.toml"
            ),
        ),
        (
            "repository_paradigm_retained_step:.config/ci/retained-steps.toml:step[0].windows",
            (
                "re-record the edited step after re-justifying it, or remove windows from this "
                "record when the job no longer needs a retained shell program"
            ),
        ),
    ]


def test_each_listed_job_must_carry_the_recorded_step(tmp_path: Path) -> None:
    """A matching sibling cannot keep a deleted copy alive, and an unlisted copy is not admitted."""
    body = _GLUE_STEP.split("\n", 1)[1]
    pipeline = (
        f"windows:\n{body}windows-review:\n{body}windows-release:\n  script: [mise run release]\n"
    )
    files = {
        ".gitlab-ci.yml": pipeline,
        _RECORD: _record(_GLUE, jobs=["windows", "windows-release"]),
    }
    assert _identities(tmp_path, files) == [
        "repository_paradigm_inline_shell:.gitlab-ci.yml:windows-review.script[0]",
        "repository_paradigm_retained_step:.config/ci/retained-steps.toml:step[0].windows-release",
    ]


def test_github_glue_is_retained_by_its_job(tmp_path: Path) -> None:
    """A GitHub run step is named by its workflow file and job like a GitLab entry."""
    workflow = "on: push\njobs:\n  native:\n    steps:\n      - run: " + json.dumps(_GLUE) + "\n"
    files = {
        ".github/workflows/verify.yml": workflow,
        _RECORD: _record(_GLUE, file=".github/workflows/verify.yml", jobs=["native"]),
    }
    assert _gaps(tmp_path, files) == []


@pytest.mark.parametrize(
    "fields",
    [
        {"evidence": None},
        {"evidence": " "},
        {"owner": ""},
        {"class": "convenience"},
        {"platforms": ["beos"]},
        {"platforms": []},
        {"jobs": []},
        {"jobs": ["windows", "windows"]},
        {"sha256": "ABC"},
        {"waiver": "always"},
    ],
    ids=[
        "no-evidence",
        "blank-evidence",
        "blank-owner",
        "uncatalogued-class",
        "uncatalogued-platform",
        "no-platforms",
        "no-jobs",
        "duplicate-job",
        "malformed-digest",
        "unknown-key",
    ],
)
def test_an_incomplete_record_admits_nothing(tmp_path: Path, fields: dict[str, object]) -> None:
    """The scenario's record without evidence or with an uncatalogued value is reported itself."""
    files = {".gitlab-ci.yml": _GLUE_STEP, _RECORD: _record(_GLUE, **fields)}
    gaps = dict(_gaps(tmp_path, files))
    assert sorted(gaps) == [
        "repository_paradigm_inline_shell:.gitlab-ci.yml:windows.script[0]",
        "repository_paradigm_retained_step:.config/ci/retained-steps.toml:step[0]",
    ]
    assert gaps["repository_paradigm_retained_step:.config/ci/retained-steps.toml:step[0]"] == (
        "give each [[step]] exactly file, jobs, sha256, class, owner, reason, platforms and "
        "evidence: distinct jobs and platforms, a class from official-installer, "
        "operating-system-glue, platforms from darwin, linux, windows, and the lowercase "
        "SHA-256 of the step text"
    )


@pytest.mark.parametrize("record", ["[[step]\n", "step = 1\n", "[[step]]\n[step.file]\n"])
def test_an_unreadable_record_is_reported(tmp_path: Path, record: str) -> None:
    """A record that is not TOML with `[[step]]` tables admits no step and is reported."""
    files = {".gitlab-ci.yml": _GLUE_STEP, _RECORD: record}
    assert (
        _identities(tmp_path, files)[0]
        == "repository_paradigm_inline_shell:.gitlab-ci.yml:windows.script[0]"
    )
    assert any(
        gap.startswith(f"repository_paradigm_retained_step:{_RECORD}")
        for gap in _identities(tmp_path, files)
    )


def test_a_gate_cannot_be_retained(tmp_path: Path) -> None:
    """The scenario's gate keeps its inline shell gap, and a record naming it matches nothing."""
    command = '["bash", "-c", "gitleaks dir ."]'
    files = {
        ".ethos/profile.toml": _PROFILE,
        "system/gates.toml": _REGISTRY.format(command=command),
        _RECORD: _record("gitleaks dir .", file="system/gates.toml", jobs=["secrets"]),
    }
    assert _identities(tmp_path, files) == [
        "repository_paradigm_inline_shell:system/gates.toml:gates.secrets",
        "repository_paradigm_retained_step:.config/ci/retained-steps.toml:step[0].secrets",
    ]


def test_a_step_running_a_tracked_script_is_not_retained(tmp_path: Path) -> None:
    """Retention admits inline shell only; a tracked script keeps its own admission path."""
    script = "tools/ci/run.sh"
    files = {
        script: "#!/bin/sh\nmise run check\n",
        ".gitlab-ci.yml": f"windows:\n  script: [{script}]\n",
        _RECORD: _record(script),
    }
    assert _identities(tmp_path, files) == [
        "repository_paradigm_retained_step:.config/ci/retained-steps.toml:step[0].windows",
        "repository_paradigm_shell_orchestration:.gitlab-ci.yml:windows.script[0]",
    ]
