"""Repository paradigm conformance over tracked paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.report import paradigm_path_gaps
from ethos.repository.paradigm.report import repository_paradigm_report
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_PYTHON_CEILING = load_repository_paradigm().size.python_effective_lines
_MODULE = "src/sample/module.py"
_PRETTIER = ".config/checks/prettier/prettier.toml"
_TAPLO = ".config/checks/taplo/taplo.toml"
_RUFF = ".config/checks/ruff/ruff.toml"


def _conforming_without(*paths: str) -> dict[str, str]:
    """Return the conforming tree without the given carriers."""
    return {path: text for path, text in CONFORMING.items() if path not in paths}


def test_conforming_repository_passes_with_product_owned_layout(tmp_path: Path) -> None:
    """Different product trees conform when every protocol carrier is in place."""
    report = paradigm_report(tmp_path, CONFORMING)
    assert report["verdict"] == "pass", report
    assert report["required_gaps"] == []
    assert report["next_action"] == ""


_CARRIER_GAPS = {
    "misplaced-config": (
        {"pytest.ini": "[pytest]\n"},
        "repository_paradigm_root_catalog:pytest.ini",
        "move pytest.ini to .config/checks/pytest/pytest.toml",
    ),
    "agent-entry": (
        {"CLAUDE.md": "@AGENTS.md\n"},
        "repository_paradigm_root_catalog:CLAUDE.md",
        "remove CLAUDE.md from the root",
    ),
    "host-root": (
        {".claude/settings.json": "{}\n"},
        "repository_paradigm_root_catalog:.claude",
        "remove .claude from the root",
    ),
    "legacy-binding": (
        {".ethos/assistants.toml": ""},
        "repository_paradigm_binding_files:.ethos/assistants.toml",
        "move .ethos/assistants.toml into an ETHOS binding file",
    ),
    "binding-state": (
        {".ethos/state/lease.json": "{}\n"},
        "repository_paradigm_binding_files:.ethos/state/lease.json",
        "remove it",
    ),
    "gitattributes": (
        {".gitattributes": "*.png binary\n"},
        "repository_paradigm_text_normalization:.gitattributes",
        "declare `* text=auto eol=lf`",
    ),
    "gitattributes-overridden": (
        {".gitattributes": "* text=auto eol=lf\n* -text\n"},
        "repository_paradigm_text_normalization:.gitattributes",
        "as the last pattern for every file",
    ),
    "editorconfig": (
        {".editorconfig": "[*]\ncharset = utf-8\nend_of_line = crlf\n"},
        "repository_paradigm_text_normalization:.editorconfig",
        "insert_final_newline = true under [*]",
    ),
    "floor": (
        {"pyproject.toml": '[project]\nname = "sample"\nrequires-python = ">=3.11"\n'},
        "repository_paradigm_module_floor:pyproject.toml",
        "lower bound >=3.12",
    ),
    "pyproject-invalid": (
        {"pyproject.toml": "[project\n"},
        "repository_paradigm_module_floor:pyproject.toml",
        "lower bound >=3.12",
    ),
    "project-not-table": (
        {"pyproject.toml": 'project = "flat"\n'},
        "repository_paradigm_module_floor:pyproject.toml",
        "lower bound >=3.12",
    ),
    "specifier-not-text": (
        {"pyproject.toml": '[project]\nname = "sample"\nrequires-python = 312\n'},
        "repository_paradigm_module_floor:pyproject.toml",
        "lower bound >=3.12",
    ),
    "npm-unlocked": (
        {"package.json": '{"devDependencies": {"prettier": "3.9.9"}}\n'},
        "repository_paradigm_module_lock:package.json",
        "lock package.json with package-lock.json",
    ),
    "npm-not-object": (
        {"package.json": "[1, 2]\n"},
        "repository_paradigm_module_lock:package.json",
        "lock package.json with package-lock.json",
    ),
    "npm-invalid": (
        {"package.json": "{invalid\n"},
        "repository_paradigm_module_lock:package.json",
        "lock package.json with package-lock.json",
    ),
    "go-unlocked": (
        {"go.mod": "module example.com/sample\n\nrequire example.com/dependency v1.0.0\n"},
        "repository_paradigm_module_lock:go.mod",
        "lock go.mod with go.sum",
    ),
    "configuration-readme": (
        {".config/README.md": "# Configuration\n"},
        "repository_paradigm_configuration_carrier:.config/README.md",
        "into the documentation",
    ),
    "configuration-by-concern": (
        {".config/checks/secrets/gitleaks.toml": ""},
        "repository_paradigm_configuration_owner:.config/checks/secrets/gitleaks.toml",
        "to .config/checks/gitleaks/gitleaks.toml",
    ),
    "configuration-not-toml": (
        {".config/checks/prettier/.prettierrc.json": "{}\n"},
        "repository_paradigm_configuration_owner:.config/checks/prettier/.prettierrc.json",
        "to .config/checks/prettier/prettier.toml",
    ),
    "configuration-unconsumed": (
        {".config/checks/ci-projection/templates.toml": ""},
        "repository_paradigm_configuration_carrier:.config/checks/ci-projection/templates.toml",
        "or .config/checks/ci-projection/policy.toml",
    ),
    "configuration-nested": (
        {".config/checks/coverage/nested/coverage.toml": ""},
        "repository_paradigm_configuration_owner:.config/checks/coverage/nested/coverage.toml",
        "to .config/checks/coverage/coverage.toml",
    ),
    "configuration-owner-name": (
        {".config/checks/Spelling_Rules/policy.toml": ""},
        "repository_paradigm_configuration_owner:.config/checks/Spelling_Rules/policy.toml",
        "in kebab-case",
    ),
    "configuration-loose": (
        {".config/release/supply-chain.toml": ""},
        "repository_paradigm_configuration_group:.config/release/supply-chain.toml",
        "under .config/<checks|release>/<owner>/",
    ),
    "configuration-group": (
        {".config/ethos/state.toml": ""},
        "repository_paradigm_configuration_group:.config/ethos/state.toml",
        "or a toolchain root",
    ),
    "embedded-manifest-table": (
        {
            "pyproject.toml": '[project]\nname = "sample"\nrequires-python = ">=3.12"\n'
            '[tool.pytest.ini_options]\ncache_dir = "build"\n[tool.hatch.version]\npath = "V"\n'
        },
        "repository_paradigm_embedded_policy:pyproject.toml:tool.pytest",
        "move [tool.pytest] to .config/checks/pytest/pytest.toml",
    ),
    "embedded-package-key": (
        {"package.json": '{"prettier": {"printWidth": 100}, "scripts": {}}\n'},
        "repository_paradigm_embedded_policy:package.json:prettier",
        "move the package.json prettier key to .config/checks/prettier/prettier.toml",
    ),
}


@pytest.mark.parametrize(("changes", "gap", "repair"), _CARRIER_GAPS.values(), ids=_CARRIER_GAPS)
def test_paradigm_gap_names_carrier_obligation_and_repair(
    tmp_path: Path, changes: dict[str, str], gap: str, repair: str
) -> None:
    """Each non-conforming carrier yields one named gap with its canonical repair."""
    report = paradigm_report(tmp_path, {**CONFORMING, **changes})
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]
    [detail] = report["gaps"]
    assert repair in detail["repair"]
    assert report["next_action"] == detail["repair"]


_TYPESCRIPT = ".config/checks/typescript/tsconfig.json"
_FOREIGN_ECOSYSTEMS = {
    "python": ("package.json", "go.mod", "cmd/sample/main.go"),
    "node": ("pyproject.toml", "uv.lock", "noxfile.py", "go.mod", "cmd/sample/main.go"),
    "go": ("pyproject.toml", "uv.lock", "noxfile.py", "package.json"),
    "polyglot": (),
}


@pytest.mark.parametrize("ecosystem", sorted(_FOREIGN_ECOSYSTEMS))
def test_typescript_project_is_admitted_at_its_native_carrier(
    tmp_path: Path, ecosystem: str
) -> None:
    """The relocated project conforms when tsc and Knip are passed it explicitly."""
    files = _conforming_without(*_FOREIGN_ECOSYSTEMS[ecosystem])
    files[_TYPESCRIPT] = '{"compilerOptions": {"checkJs": true}, "include": ["../../../src"]}\n'
    files[".config/checks/knip/knip.toml"] = f'[typescript]\nconfig = "{_TYPESCRIPT}"\n'
    if "package.json" in files:
        files["package.json"] = (
            '{"scripts": {"check:types": "tsc --project ' + _TYPESCRIPT + ' --noEmit", '
            '"check:dead-code": "knip --config .config/checks/knip/knip.toml"}}\n'
        )

    report = paradigm_report(tmp_path, files)

    assert report["verdict"] == "pass", report
    assert paradigm_path_gaps(_TYPESCRIPT) == ()


@pytest.mark.parametrize(
    ("path", "obligation"),
    [
        ("tsconfig.json", "root_catalog"),
        ("jsconfig.json", "root_catalog"),
        (".config/checks/knip/tsconfig.json", "configuration_owner"),
    ],
)
def test_typescript_project_elsewhere_names_its_native_carrier(
    tmp_path: Path, path: str, obligation: str
) -> None:
    """A TypeScript project file anywhere else is a gap whose repair moves it to the carrier."""
    report = paradigm_report(tmp_path, {**CONFORMING, path: "{}\n"})
    assert report["required_gaps"] == [f"repository_paradigm_{obligation}:{path}"]
    assert f"{path} to {_TYPESCRIPT}" in report["next_action"]


def test_missing_entries_and_unlocked_runner_are_reported(tmp_path: Path) -> None:
    """A runner entry needs its module, and entry documents and carriers must be tracked."""
    files = _conforming_without("pyproject.toml", "uv.lock")
    untracked = ("AGENTS.md", ".gitattributes", ".editorconfig")
    report = paradigm_report(tmp_path, files, untracked=untracked)
    assert report["required_gaps"] == [
        "repository_paradigm_root_catalog:noxfile.py",
        "repository_paradigm_entry_documents:AGENTS.md",
        "repository_paradigm_text_normalization:.gitattributes",
        "repository_paradigm_text_normalization:.editorconfig",
    ]


def test_python_module_requires_its_lock(tmp_path: Path) -> None:
    """A tracked Python manifest always needs uv.lock, whatever it declares."""
    report = paradigm_report(tmp_path, _conforming_without("uv.lock"))
    assert report["required_gaps"] == ["repository_paradigm_module_lock:pyproject.toml"]
    assert report["next_action"] == "lock pyproject.toml with uv.lock"


def _damaged_report(root: Path, files: dict[str, str], path: str, damage: bytes | None) -> dict:
    """Track the files, then overwrite one with the damage or delete it, and report again."""
    paradigm_report(root, files)
    if damage is None:
        (root / path).unlink()
    else:
        (root / path).write_bytes(damage)
    return repository_paradigm_report(root, tracked_paths=tuple(files))


@pytest.mark.parametrize("damage", [b"\xff\xfe", None], ids=["unreadable", "absent"])
def test_unreadable_tracked_manifest_is_a_gap(tmp_path: Path, damage: bytes | None) -> None:
    """A tracked manifest that cannot be read never passes as unlocked or unfloored."""
    report = _damaged_report(tmp_path, CONFORMING, "pyproject.toml", damage)
    assert report["required_gaps"] == ["repository_paradigm_module_lock:pyproject.toml"]
    repair = "restore a readable pyproject.toml"
    assert report["gaps"] == [
        {"obligation": "module-lock", "carrier": "pyproject.toml", "repair": repair}
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
    report = paradigm_report(tmp_path, {**CONFORMING, _MODULE: source})
    assert report["required_gaps"] == gaps
    if gaps:
        assert _MODULE in report["next_action"]


@pytest.mark.parametrize("damage", [b"name = '\xff'\n", None], ids=["undecodable", "absent"])
def test_python_size_reads_only_what_exists_as_text(tmp_path: Path, damage: bytes | None) -> None:
    """Undecodable source is a gap; a tracked file deleted from the worktree is not measured."""
    report = _damaged_report(tmp_path, {**CONFORMING, _MODULE: "value = 1\n"}, _MODULE, damage)
    expected = [f"repository_paradigm_python_size:{_MODULE}"] if damage else []
    assert report["required_gaps"] == expected


def test_a_binding_cannot_restate_the_size_ceiling(tmp_path: Path) -> None:
    """The ceiling has one owner, so a repository-declared limit is a gap, not a setting."""
    rules = "[quality.code_size]\ndefault_effective_max_lines = 900\n"
    report = paradigm_report(tmp_path, {**CONFORMING, ".ethos/rules.toml": rules})
    assert report["required_gaps"] == [
        "repository_paradigm_binding_restatement:.ethos/rules.toml:quality.code_size"
    ]


@pytest.mark.parametrize(
    ("changes", "gap", "repair"),
    [
        ({_PRETTIER: None}, "formatter_binding", "bind prettier"),
        (
            {_PRETTIER: 'printWidth = 80\nproseWrap = "always"\n'},
            "formatter_setting",
            "set proseWrap to 'preserve'",
        ),
        ({_TAPLO: "[formatting]\n"}, "formatter_setting", "column_width"),
        ({_RUFF: "line-length = 100\n"}, "formatter_setting", "py312"),
    ],
    ids=["unbound", "settings", "nested-setting", "python-target"],
)
def test_each_tracked_carrier_class_names_its_common_formatter(
    tmp_path: Path, changes: dict[str, str | None], gap: str, repair: str
) -> None:
    """A carrier class present in the tree needs its formatter bound with common settings."""
    files = {key: value for key, value in {**CONFORMING, **changes}.items() if value is not None}
    report = paradigm_report(tmp_path, files)
    assert report["verdict"] == "block"
    assert [item for item in report["required_gaps"] if gap in item], report["required_gaps"]
    assert any(repair in detail["repair"] for detail in report["gaps"]), report["gaps"]


def test_formatter_accepted_markdown_layout_conforms(tmp_path: Path) -> None:
    """The shared formatter owns Markdown layout, so a loose list it accepts is no paradigm gap."""
    guide = "content/guide.md"
    loose = "---\nsubject: sample:guide\n---\n\n# Guide\n\n- First.\n\n- Second.\n"

    report = paradigm_report(tmp_path, {**CONFORMING, guide: loose})

    assert [gap for gap in report["gaps"] if gap["carrier"] == guide] == []


def test_a_carrier_class_only_inside_an_immutable_root_needs_no_formatter(tmp_path: Path) -> None:
    """A repository with no current Python needs no Ruff binding, archived files aside."""
    files = _conforming_without("pyproject.toml", "uv.lock", "noxfile.py", _RUFF)
    archived = "openspec/changes/archive/2026-01-01-old/probe.py"
    report = paradigm_report(tmp_path, {**files, archived: "value = 1\n"})
    assert report["required_gaps"] == [], report["required_gaps"]
