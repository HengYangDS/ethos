"""Bind native Node recipes to independently selected Git tests and same-attempt evidence."""

from __future__ import annotations

import glob
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

from ethos.adapters.gates.javascript.behavior import behavior_observation
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.code_subjects import CodeSubject
from ethos.repository.policy.quality_reports import validate_native_v8_report
from tests.support.governed_repository import committed_source_repo


@pytest.mark.parametrize("selection", ["default", "option-only", "explicit"])
def test_native_selection_preserves_options_and_same_attempt_custody(
    tmp_path: Path, selection: str
) -> None:
    """Git-selected cohorts run once; a native explicit omission remains unproved."""
    node = shutil.which("node")
    assert node is not None
    tests = ("tests/current/answer.test.mjs", "tests/new domain/[id]/answer.test.mjs")
    recipe = (
        "node --import=./preload.mjs --test --test-concurrency=2 --test-timeout=180000"
        if selection == "option-only"
        else None
        if selection == "default"
        else "node --import ./preload.mjs --test --test-concurrency=2 "
        "--test-timeout=180000 " + tests[0]
    )
    body = (
        'import {test} from "node:test"; import {appendFileSync} from "node:fs";\n'
        'import {answer} from "../../src/answer.mjs";\n'
        'test("answer", () => { appendFileSync("attempts", "one\\n"); '
        'if (answer() !== globalThis.nativeAnswer) throw Error("preload missing"); });\n'
    )
    if selection == "default":
        body = body.replace("globalThis.nativeAnswer", "42")
    scripts = {"test": recipe} if recipe else {}
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitignore": "attempts\ntests/generated/\ntests/new domain/i/\n",
            "package.json": json.dumps(
                {"scripts": scripts | {"test:coverage": "c8 --include=src/answer.mjs npm test"}}
            ),
            "src/answer.mjs": "export function answer() { return 42; }\n",
            "preload.mjs": "globalThis.nativeAnswer = 42;\n",
            tests[0]: body,
        },
    )
    candidate = repo / tests[1]
    candidate.parent.mkdir(parents=True)
    candidate.write_text(body.replace("../../src/", "../../../src/"))
    ignored = repo / "tests/generated/ignored.test.mjs"
    ignored.parent.mkdir()
    ignored.write_text('throw Error("ignored test was selected");\n')
    neighbor = repo / "tests/new domain/i/answer.test.mjs"
    neighbor.parent.mkdir()
    neighbor.write_text('throw Error("raw glob neighbor was selected");\n')
    inventory = subprocess.run(
        ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert inventory.returncode == 0, inventory.stderr
    selected = tuple(
        sorted(path for path in inventory.stdout.split("\0") if path.endswith(".test.mjs"))
    )
    assert selected == tests
    subjects = (
        CodeSubject("src/answer.mjs", "javascript", is_test=False),
        CodeSubject("preload.mjs", "javascript", is_test=False, role="tooling"),
        *(CodeSubject(path, "javascript", is_test=True) for path in selected),
    )
    report = behavior_observation(repo, subjects, None, node, {}, timeout_seconds=180)
    assert report["verdict"] == ("block" if selection == "explicit" else "pass"), report
    argv = string_sequence(string_mapping(report["test_execution"])["argv"])
    assert ("--test-concurrency=2" in argv) is (selection != "default")
    assert ("--test-timeout=180000" in argv) is (selection != "default")
    assert "--include=src/answer.mjs" in string_sequence(
        string_mapping(report["coverage_execution"])["argv"]
    )
    if selection != "explicit":
        assert tuple(argv[-2:]) == tuple(map(glob.escape, selected))
        assert ("--import=./preload.mjs" in argv) is (selection == "option-only")
        assert {key: string_mapping(report["tests"])[key] for key in ("total", "passed")} == {
            "total": 2,
            "passed": 2,
        }
        assert (repo / "attempts").read_text() == "one\none\n"
        assert report["required_gaps"] == []
    else:
        assert tuple(argv[-3:]) == ("--test-concurrency=2", "--test-timeout=180000", tests[0])
        assert "--import" in argv
        assert "./preload.mjs" in argv
        assert "javascript_native_test_scope_incomplete" in string_sequence(report["required_gaps"])
        assert (repo / "attempts").read_text() == "one\n"
    assert report["raw_identity_preserved"]
    assert not Path(str(report["raw_directory"])).exists()
    identity = string_mapping(report["raw_identity"])
    assert identity
    with ZipFile(str(string_mapping(report["artifact"])["path"])) as archive:
        for name, digest in identity.items():
            content = archive.read(f"raw/{name}")
            validate_native_v8_report(content)
            assert hashlib.sha256(content).hexdigest() == digest


@pytest.mark.parametrize("lifecycle", ["pretest", "posttest"])
def test_unsupported_lifecycle_is_not_silently_skipped(tmp_path: Path, lifecycle: str) -> None:
    """Option-only composition does not authorize omission of an npm lifecycle effect."""
    (tmp_path / "package.json").write_text(
        json.dumps(
            {"scripts": {"test": "node --test --test-concurrency=2", lifecycle: "node prepare.mjs"}}
        )
    )
    subjects = (
        CodeSubject("answer.mjs", "javascript", is_test=False),
        CodeSubject("answer.test.mjs", "javascript", is_test=True),
    )
    with pytest.raises(ValueError, match=r"^javascript_native_recipe_unsupported$"):
        behavior_observation(tmp_path, subjects, None, "node", {}, timeout_seconds=180)
