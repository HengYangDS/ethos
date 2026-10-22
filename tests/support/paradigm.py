"""A conforming repository tree and a report helper for repository paradigm tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.report import repository_paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_OPENSPEC = load_repository_paradigm().openspec
PARADIGM_OPENSPEC_CONFIG = yaml.safe_dump(
    {"schema": _OPENSPEC.artifact_schema, "rules": _OPENSPEC.rules.model_dump(mode="json")},
    sort_keys=False,
)
CONFORMING = {
    "AGENTS.md": "# Agents\n",
    "README.md": "# Sample\n",
    ".gitattributes": "* text=auto eol=lf\n",
    ".editorconfig": (
        "root = true\n\n# all files\n[*]\ncharset = UTF-8\nend_of_line = lf\n"
        "insert_final_newline = true\n\n[*.py]\nindent_size = 4\n"
    ),
    "pyproject.toml": '[project]\nname = "sample"\nrequires-python = ">=3.12,<3.15"\n',
    "uv.lock": "version = 1\n",
    "noxfile.py": "",
    "package.json": '{"scripts": {"check": "node check.mjs"}}\n',
    "go.mod": "module example.com/sample\n",
    ".ethos/profile.toml": 'profile_id = "sample"\n',
    "cmd/sample/main.go": "package main\n",
    "content/intro.md": "# Intro\n",
    "docs/decisions/README.md": "---\nsubject: sample:decisions\n---\n\n# Decisions\n",
    "docs/decisions/decision-index.md": "---\nsubject: sample:index\n---\n\n# Index\n",
    "docs/decisions/dr-0001-layout.md": "---\nsubject: sample:layout\n---\n\n# Layout\n",
    ".config/miserc.toml": "",
    ".config/mise/config.toml": (
        '[settings]\nlocked = true\n\n[tasks]\nbootstrap = "uv sync --locked"\n'
        'check = "uv run nox -s check"\nfix = "uv run nox -s fix"\n'
    ),
    ".config/mise/mise.lock": "",
    ".config/npm/npmrc": "",
    ".config/ci/pipeline.cue": "",
    ".config/checks/ruff/ruff.toml": 'line-length = 100\ntarget-version = "py312"\n',
    ".config/checks/prettier/prettier.toml": 'printWidth = 100\nproseWrap = "preserve"\n',
    ".config/checks/taplo/taplo.toml": "[formatting]\ncolumn_width = 100\n",
    ".config/checks/gitleaks/gitleaksignore": "",
    ".config/checks/coverage/coverage.toml": "",
    ".config/checks/coverage/policy.toml": "",
    ".config/checks/architecture-projection/policy.toml": "",
    ".config/checks/vale/vale.ini": "",
    ".config/checks/vale/styles/plain/rule.yml": "",
    ".config/release/goreleaser/.goreleaser.yaml": "",
    "openspec/config.yaml": PARADIGM_OPENSPEC_CONFIG,
}


def paradigm_report(
    root: Path,
    files: dict[str, str],
    *,
    untracked: tuple[str, ...] = (),
    received: tuple[str, ...] = (),
    line_endings: dict[str, tuple[str, str]] | None = None,
) -> dict:
    """Write the files under root and evaluate the paradigm over the tracked ones.

    Every tracked file checks out with LF unless `line_endings` gives its Git attributes.
    """
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    tracked = tuple(path for path in files if path not in untracked)
    return repository_paradigm_report(
        root,
        tracked_paths=tracked,
        received_paths=received,
        line_endings=conforming_checkout(tracked) | (line_endings or {}),
    )


def conforming_checkout(tracked: tuple[str, ...]) -> dict[str, tuple[str, str]]:
    """Return the Git text and eol attributes the shared rule gives every tracked file."""
    return dict.fromkeys(tracked, ("auto", "lf"))
