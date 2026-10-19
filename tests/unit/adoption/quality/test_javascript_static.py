"""JavaScript static quality: lexical correctness and declared execution environments."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.javascript.analysis as analysis
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("source", "verdict"),
    [
        ("export function answer() { return undefined_value; }\n", "block"),
        (
            "/* eslint-disable no-undef */\nexport function answer() { return undefined_value; }\n",
            "block",
        ),
        ("export function answer(undefined_value) { return undefined_value; }\n", "pass"),
        ("export function answer() { return 42; }\n", "pass"),
    ],
)
@pytest.mark.parametrize("role", ["code", "snapshot"])
def test_javascript_static_quality_preserves_lexical_bindings(
    tmp_path: Path,
    source: str,
    verdict: str,
    role: str,
) -> None:
    """Syntax success cannot certify declared lexical correctness or suppress its diagnostics."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / "package.json").write_text('{"type":"module"}\n')
    (repo / "answer.js").write_text(source)
    (repo / ".gitattributes").write_text(f"answer.js ethos-role={role}\n")
    commit_fixture(repo, "lexical quality source")
    report = native_quality.static_report(repo)
    assert report["verdict"] == ("block" if role == "snapshot" else verdict), report
    if role == "snapshot":
        assert report["required_gaps"] == [
            "quality_static-analysis_source_contract_missing:answer.js"
        ]
        assert "native" not in report
    elif verdict == "block":
        assert report["required_gaps"]


_BROWSER_CALLBACK = (
    "export async function size(page) {\n  return page.evaluate(() => window.innerWidth);\n}\n"
)


@pytest.mark.parametrize(
    ("policy", "verdict"),
    [
        (None, "block"),
        (
            (
                '[[environment]]\npaths = ["render.mjs"]\nglobals = ["browser"]\n'
                'reason = "page.evaluate runs this callback in the browser"\n'
            ),
            "pass",
        ),
        (
            '[[environment]]\npaths = ["render.mjs"]\nglobals = ["node"]\nreason = "x"\n',
            "block",
        ),
        ('[[environment]]\npaths = ["render.mjs"]\nglobals = ["browser"]\n', "block"),
        (
            '[[environment]]\npaths = ["missing.mjs"]\nglobals = ["browser"]\nreason = "x"\n',
            "block",
        ),
        ("[[environment]\n", "block"),
        ("", "block"),
    ],
    ids=["undeclared", "declared", "unknown-set", "no-reason", "untracked-path", "syntax", "empty"],
)
def test_javascript_static_quality_admits_only_a_declared_execution_environment(
    tmp_path: Path, policy: str | None, verdict: str
) -> None:
    """A browser callback passes only under a validated declaration bound to its own file."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / "package.json").write_text('{"type":"module"}\n')
    (repo / "render.mjs").write_text(_BROWSER_CALLBACK)
    if policy is not None:
        declaration = repo / ".config/checks/eslint/policy.toml"
        declaration.parent.mkdir(parents=True)
        declaration.write_text(policy)
    commit_fixture(repo, "browser callback source")
    report = native_quality.static_report(repo)
    assert report["verdict"] == verdict, report
    # A refused declaration stops before ESLint; an absent or valid one lets ESLint judge.
    assert ("native" in report) is (policy is None or verdict == "pass"), report


def test_a_declared_environment_does_not_extend_to_other_files(tmp_path: Path) -> None:
    """Only the declared path gains the browser globals; another file still fails no-undef."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / "package.json").write_text('{"type":"module"}\n')
    (repo / "render.mjs").write_text(_BROWSER_CALLBACK)
    (repo / "server.mjs").write_text("export const width = window.innerWidth;\n")
    declaration = repo / ".config/checks/eslint/policy.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        '[[environment]]\npaths = ["render.mjs"]\nglobals = ["browser"]\n'
        'reason = "page.evaluate runs this callback in the browser"\n'
    )
    commit_fixture(repo, "declared and undeclared sources")
    report = native_quality.static_report(repo)
    assert report["verdict"] == "block", report
    native = report["native"][0]
    assert native["environments"] == {"render.mjs": ["browser"]}
    failing = {
        item["filePath"].rsplit("/", 1)[-1] for item in native["reports"] if item["errorCount"]
    }
    assert failing == {"server.mjs"}


@pytest.mark.parametrize(
    ("name", "reported", "gap"),
    [
        ("answer.js", "answer.js", "javascript_package_type_invalid"),
        ("answer.cjs", "other.cjs", "javascript_static_report_invalid"),
        ("answer.cjs", "answer.cjs", "javascript_static_source_changed"),
    ],
)
def test_eslint_reports_bind_the_unchanged_source(tmp_path, monkeypatch, name, reported, gap):
    """Only .js reads the package type; ESLint must report each requested file, unchanged."""
    (tmp_path / "package.json").write_text('{"type": "esm"}\n')
    (tmp_path / name).write_text("module.exports = 42;\n")
    report = {"filePath": tmp_path / reported, "messages": [], "errorCount": 0, "warningCount": 0}

    # The ESLint process is the only substituted boundary; it edits the source as it runs.
    def eslint(*_args, **_options):
        (tmp_path / name).write_text("module.exports = 43;\n")
        return subprocess.CompletedProcess((), 0, json.dumps([report], default=str), "")

    monkeypatch.setattr(analysis, "run_command", eslint)
    with pytest.raises(ValueError, match=f"^{gap}$"):
        analysis.static_observation(tmp_path, (name,), node="node")
