"""Repository paradigm conformance over tracked paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.report import repository_paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_PYTHON_CEILING = load_repository_paradigm().size.python_effective_lines
_MODULE = "src/sample/module.py"

_CONFORMING = {
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
    ".config/miserc.toml": "",
    ".config/mise/config.toml": "",
    ".config/npm/npmrc": "",
    ".config/ci/pipeline.cue": "",
    ".config/checks/ruff/ruff.toml": "line-length = 100\n",
    ".config/checks/gitleaks/gitleaksignore": "",
    ".config/checks/coverage/coverage.toml": "",
    ".config/checks/coverage/policy.toml": "",
    ".config/checks/architecture-projection/policy.toml": "",
    ".config/checks/vale/vale.ini": "",
    ".config/checks/vale/styles/Plain/Rule.yml": "",
    ".config/release/goreleaser/.goreleaser.yaml": "",
}


def _report(root: Path, files: dict[str, str], *, untracked: tuple[str, ...] = ()) -> dict:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    tracked = tuple(path for path in files if path not in untracked)
    return repository_paradigm_report(root, tracked_paths=tracked)


def test_conforming_repository_passes_with_product_owned_layout(tmp_path: Path) -> None:
    """Different product trees conform when every protocol carrier is in place."""
    report = _report(tmp_path, _CONFORMING)
    assert report["verdict"] == "pass", report
    assert report["required_gaps"] == []
    assert report["next_action"] == ""


@pytest.mark.parametrize(
    ("changes", "gap", "repair"),
    [
        (
            {"pytest.ini": "[pytest]\n"},
            "repository_paradigm_root_catalog:pytest.ini",
            "move pytest.ini to .config/checks/pytest/pytest.toml",
        ),
        (
            {"CLAUDE.md": "@AGENTS.md\n"},
            "repository_paradigm_root_catalog:CLAUDE.md",
            "remove CLAUDE.md from the root",
        ),
        (
            {".claude/settings.json": "{}\n"},
            "repository_paradigm_root_catalog:.claude",
            "remove .claude from the root",
        ),
        (
            {".ethos/assistants.toml": ""},
            "repository_paradigm_binding_files:.ethos/assistants.toml",
            "move .ethos/assistants.toml into an ETHOS binding file",
        ),
        (
            {".ethos/state/lease.json": "{}\n"},
            "repository_paradigm_binding_files:.ethos/state/lease.json",
            "remove it",
        ),
        (
            {".gitattributes": "*.png binary\n"},
            "repository_paradigm_text_normalization:.gitattributes",
            "declare `* text=auto eol=lf`",
        ),
        (
            {".gitattributes": "* text=auto eol=lf\n* -text\n"},
            "repository_paradigm_text_normalization:.gitattributes",
            "as the last pattern for every file",
        ),
        (
            {".editorconfig": "[*]\ncharset = utf-8\nend_of_line = crlf\n"},
            "repository_paradigm_text_normalization:.editorconfig",
            "insert_final_newline = true under [*]",
        ),
        (
            {"pyproject.toml": '[project]\nname = "sample"\nrequires-python = ">=3.11"\n'},
            "repository_paradigm_module_floor:pyproject.toml",
            "lower bound >=3.12",
        ),
        (
            {"pyproject.toml": "[project\n"},
            "repository_paradigm_module_floor:pyproject.toml",
            "lower bound >=3.12",
        ),
        (
            {"pyproject.toml": 'project = "flat"\n'},
            "repository_paradigm_module_floor:pyproject.toml",
            "lower bound >=3.12",
        ),
        (
            {"pyproject.toml": '[project]\nname = "sample"\nrequires-python = 312\n'},
            "repository_paradigm_module_floor:pyproject.toml",
            "lower bound >=3.12",
        ),
        (
            {"package.json": '{"devDependencies": {"prettier": "3.9.9"}}\n'},
            "repository_paradigm_module_lock:package.json",
            "lock package.json with package-lock.json",
        ),
        (
            {"package.json": "[1, 2]\n"},
            "repository_paradigm_module_lock:package.json",
            "lock package.json with package-lock.json",
        ),
        (
            {"package.json": "{invalid\n"},
            "repository_paradigm_module_lock:package.json",
            "lock package.json with package-lock.json",
        ),
        (
            {"go.mod": "module example.com/sample\n\nrequire example.com/dependency v1.0.0\n"},
            "repository_paradigm_module_lock:go.mod",
            "lock go.mod with go.sum",
        ),
        (
            {".config/README.md": "# Configuration\n"},
            "repository_paradigm_configuration_carrier:.config/README.md",
            "into the documentation",
        ),
        (
            {".config/checks/secrets/gitleaks.toml": ""},
            "repository_paradigm_configuration_owner:.config/checks/secrets/gitleaks.toml",
            "to .config/checks/gitleaks/gitleaks.toml",
        ),
        (
            {".config/checks/prettier/.prettierrc.json": "{}\n"},
            "repository_paradigm_configuration_owner:.config/checks/prettier/.prettierrc.json",
            "to .config/checks/prettier/prettier.toml",
        ),
        (
            {".config/checks/ci-projection/templates.toml": ""},
            "repository_paradigm_configuration_carrier:.config/checks/ci-projection/templates.toml",
            "or .config/checks/ci-projection/policy.toml",
        ),
        (
            {".config/checks/coverage/nested/coverage.toml": ""},
            "repository_paradigm_configuration_owner:.config/checks/coverage/nested/coverage.toml",
            "to .config/checks/coverage/coverage.toml",
        ),
        (
            {".config/checks/Spelling_Rules/policy.toml": ""},
            "repository_paradigm_configuration_owner:.config/checks/Spelling_Rules/policy.toml",
            "in kebab-case",
        ),
        (
            {".config/release/supply-chain.toml": ""},
            "repository_paradigm_configuration_group:.config/release/supply-chain.toml",
            "under .config/<checks|release>/<owner>/",
        ),
        (
            {".config/ethos/state.toml": ""},
            "repository_paradigm_configuration_group:.config/ethos/state.toml",
            "or a toolchain root",
        ),
        (
            {
                "pyproject.toml": '[project]\nname = "sample"\nrequires-python = ">=3.12"\n'
                '[tool.pytest.ini_options]\ncache_dir = "build"\n[tool.hatch.version]\npath = "V"\n'
            },
            "repository_paradigm_embedded_policy:pyproject.toml:tool.pytest",
            "move [tool.pytest] to .config/checks/pytest/pytest.toml",
        ),
        (
            {"package.json": '{"prettier": {"printWidth": 100}, "scripts": {}}\n'},
            "repository_paradigm_embedded_policy:package.json:prettier",
            "move the package.json prettier key to .config/checks/prettier/prettier.toml",
        ),
    ],
    ids=[
        "misplaced-config",
        "agent-entry",
        "host-root",
        "legacy-binding",
        "binding-state",
        "gitattributes",
        "gitattributes-overridden",
        "editorconfig",
        "floor",
        "pyproject-invalid",
        "project-not-table",
        "specifier-not-text",
        "npm-unlocked",
        "npm-not-object",
        "npm-invalid",
        "go-unlocked",
        "configuration-readme",
        "configuration-by-concern",
        "configuration-not-toml",
        "configuration-unconsumed",
        "configuration-nested",
        "configuration-owner-name",
        "configuration-loose",
        "configuration-group",
        "embedded-manifest-table",
        "embedded-package-key",
    ],
)
def test_paradigm_gap_names_carrier_obligation_and_repair(
    tmp_path: Path, changes: dict[str, str], gap: str, repair: str
) -> None:
    """Each non-conforming carrier yields one named gap with its canonical repair."""
    report = _report(tmp_path, {**_CONFORMING, **changes})
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]
    [detail] = report["gaps"]
    assert repair in detail["repair"]
    assert report["next_action"] == detail["repair"]


def test_missing_entries_and_unlocked_runner_are_reported(tmp_path: Path) -> None:
    """A runner entry needs its module, and entry documents and carriers must be tracked."""
    files = {**_CONFORMING}
    del files["pyproject.toml"], files["uv.lock"]
    report = _report(tmp_path, files, untracked=("AGENTS.md", ".gitattributes", ".editorconfig"))
    assert report["required_gaps"] == [
        "repository_paradigm_root_catalog:noxfile.py",
        "repository_paradigm_entry_documents:AGENTS.md",
        "repository_paradigm_text_normalization:.gitattributes",
        "repository_paradigm_text_normalization:.editorconfig",
    ]


def test_python_module_requires_its_lock(tmp_path: Path) -> None:
    """A tracked Python manifest always needs uv.lock, whatever it declares."""
    files = {**_CONFORMING}
    del files["uv.lock"]
    report = _report(tmp_path, files)
    assert report["required_gaps"] == ["repository_paradigm_module_lock:pyproject.toml"]
    assert report["next_action"] == "lock pyproject.toml with uv.lock"


@pytest.mark.parametrize("mode", ["unreadable", "absent"])
def test_unreadable_tracked_manifest_is_a_gap(tmp_path: Path, mode: str) -> None:
    """A tracked manifest that cannot be read never passes as unlocked or unfloored."""
    _report(tmp_path, _CONFORMING)
    manifest = tmp_path / "pyproject.toml"
    if mode == "unreadable":
        manifest.write_bytes(b"\xff\xfe")
    else:
        manifest.unlink()
    tracked = tuple(_CONFORMING)
    report = repository_paradigm_report(tmp_path, tracked_paths=tracked)
    assert report["required_gaps"] == ["repository_paradigm_module_lock:pyproject.toml"]
    assert report["gaps"] == [
        {
            "obligation": "module-lock",
            "carrier": "pyproject.toml",
            "repair": "restore a readable pyproject.toml",
        }
    ]


def _statements(count: int) -> str:
    return "".join(f"value_{index} = {index}\n" for index in range(count))


@pytest.mark.parametrize(
    ("source", "gaps"),
    [
        (_statements(_PYTHON_CEILING), []),
        (_statements(_PYTHON_CEILING + 1), [f"repository_paradigm_python_size:{_MODULE}"]),
        ('"""' + "documentation\n" * 600 + '"""\n' + _statements(_PYTHON_CEILING), []),
        ("def invalid(\n", [f"repository_paradigm_python_size:{_MODULE}"]),
    ],
    ids=["at-ceiling", "over-ceiling", "docstring-uncounted", "invalid"],
)
def test_every_python_file_shares_one_effective_line_ceiling(
    tmp_path: Path, source: str, gaps: list[str]
) -> None:
    """The ceiling applies without any repository size policy and counts only code."""
    report = _report(tmp_path, {**_CONFORMING, _MODULE: source})
    assert report["required_gaps"] == gaps
    if gaps:
        assert _MODULE in report["next_action"]


@pytest.mark.parametrize("mode", ["undecodable", "absent"])
def test_python_size_reads_only_what_exists_as_text(tmp_path: Path, mode: str) -> None:
    """Undecodable source is a gap; a tracked file deleted from the worktree is not measured."""
    _report(tmp_path, {**_CONFORMING, _MODULE: "value = 1\n"})
    module = tmp_path / _MODULE
    if mode == "undecodable":
        module.write_bytes(b"name = '\xff'\n")
    else:
        module.unlink()
    report = repository_paradigm_report(tmp_path, tracked_paths=(*_CONFORMING, _MODULE))
    expected = [f"repository_paradigm_python_size:{_MODULE}"] if mode == "undecodable" else []
    assert report["required_gaps"] == expected


def test_a_binding_cannot_restate_the_size_ceiling(tmp_path: Path) -> None:
    """The ceiling has one owner, so a repository-declared limit is a gap, not a setting."""
    rules = "[quality.code_size]\ndefault_effective_max_lines = 900\n"
    report = _report(tmp_path, {**_CONFORMING, ".ethos/rules.toml": rules})
    assert report["required_gaps"] == [
        "repository_paradigm_binding_restatement:.ethos/rules.toml:quality.code_size"
    ]
