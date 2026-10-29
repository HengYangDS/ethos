"""References follow their executor's grammar and the declarations that supply them."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.orchestration import orchestration_gaps
from ethos.repository.policy.references.commands import shell_executables
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.declarations import retained_ci_steps
from ethos.repository.policy.references.observation import product_references_from_files

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ('v="$("${python}" -c "print(str(1))")"', set()),
        ('x="$(git rev-parse HEAD)"', {"git"}),
        ("stamp=`date -u`", {"date"}),
        ("echo 'literal $(rm -rf build)'", set()),
        ("attempt=$((attempt + 1))", set()),
        ("(( attempt += 1 ))", set()),
        ("n=$(( $(wc -l < list) + 1 ))", {"wc"}),
        ("$PYTHON -m pip install wheel", set()),
        ("$ git status", {"git"}),
        ("echo start; + next", set()),
    ],
)
def test_shell_reading_follows_posix_nesting(line: str, expected: set[str]) -> None:
    """Quotes pair within each substitution; arithmetic words and operators are values."""
    assert shell_executables(line + "\n", {}) == expected


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ("CODEX_HOME=<active-codex-home> codex doctor --json", {"codex"}),
        ("<runner> getraw run sample", set()),
        ("web-ingest --mode static|browser|crawl", {"web-ingest"}),
        ("ps aux|grep python", {"grep", "ps"}),
    ],
)
def test_documentation_metasyntax_is_not_a_command(block: str, expected: set[str]) -> None:
    """Placeholders and synopsis alternations are values; an unspaced pipeline stays one."""
    document = {"docs/guide.md": f"```bash\n{block}\n```\n"}

    observed = product_references_from_files(document, include_declarations=False).references

    assert observed["executable"] == expected


def test_scripts_keep_posix_redirection() -> None:
    """Only documentation reads `<name>` as a placeholder; a script redirects."""
    script = {"tools/ci/scripts/sort.sh": "#!/bin/sh\nsort <input >output\n"}

    observed = product_references_from_files(script, include_declarations=False).references

    assert observed["executable"] == {"sh", "sort"}


def test_a_mise_tool_owns_the_executable_it_names() -> None:
    """A tool owns its `rename_exe` or its identity's last segment; companions stay unowned."""
    config = (
        "[tools]\n"
        '"aqua:cue-lang/cue" = "0.17.1"\n'
        'rust = "1.99.1"\n'
        '"github:prefix-dev/pixi" = { version = "0.60.0", os = ["linux/arm64"] }\n'
        '"ubi:BurntSushi/ripgrep" = [{ version = "15.1.0", rename_exe = "rg" }]\n'
    )

    owned = native_owned_references_from_files({".config/mise/config.toml": config})

    assert {"cue", "pixi", "rg", "rust"} <= owned["executable"]
    assert "rustup" not in owned["executable"]


def test_package_roots_own_first_party_names() -> None:
    """A package below a directory without `__init__.py` is first-party, as deptry's names are."""
    files = {
        ".githooks/_hook/__init__.py": "",
        ".githooks/_hook/repo/__init__.py": "",
        ".githooks/_hook/repo/governance.py": "",
        ".githooks/_pre_commit/__init__.py": "",
        ".githooks/_pre_commit/entrypoint.py": "import _hook\n",
        ".config/checks/deptry/policy.toml": 'known_first_party = ["vendored"]\n',
    }

    owned = native_owned_references_from_files(files)

    assert {"_hook", "_pre_commit", "vendored"} <= owned["import"]
    assert "yaml" not in owned["import"]


_RECORD = ".config/ci/retained-steps.toml"
_POWERSHELL = (
    '$env:PATH = (Join-Path $env:ProgramFiles "mise/bin") + [IO.Path]::PathSeparator + $env:PATH'
)


def test_a_retained_powershell_step_is_owned_as_a_whole(tmp_path: Path) -> None:
    """Retention matches by file, job and digest, so a PowerShell step reads no commands."""
    pipeline = f".verify-windows:\n  before_script:\n    - {json.dumps(_POWERSHELL)}\n"
    record = "\n".join(
        (
            "[[step]]",
            'file = ".gitlab-ci.yml"',
            'jobs = [".verify-windows"]',
            f'sha256 = "{hashlib.sha256(_POWERSHELL.encode()).hexdigest()}"',
            'class = "operating-system-glue"',
            'owner = "CI pipeline model"',
            'reason = "The Windows runner finds mise only through its install directory."',
            'platforms = ["windows"]',
            'evidence = "GitLab job 1 ran it on ci-windows-arm64-shell"',
            "",
        )
    )
    files = {".gitlab-ci.yml": pipeline, _RECORD: record}
    for relative, content in files.items():
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(content, encoding="utf-8")

    gaps = list(orchestration_gaps(load_repository_paradigm(), tmp_path, frozenset(files)))
    observed = product_references_from_files(
        {".gitlab-ci.yml": pipeline},
        include_declarations=False,
        retained_steps=retained_ci_steps({_RECORD: record}),
    ).references
    edited = product_references_from_files(
        {".gitlab-ci.yml": pipeline.replace("mise/bin", "mise\\\\bin")},
        include_declarations=False,
        retained_steps=retained_ci_steps({_RECORD: record}),
    ).references

    assert [gap.required_gap for gap in gaps] == []
    assert "Join-Path" not in observed["executable"]
    assert "Join-Path" in edited["executable"]
