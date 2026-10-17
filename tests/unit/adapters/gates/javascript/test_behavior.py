"""Keep one native JavaScript test attempt and its failures as conserved evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

import ethos.adapters.gates.javascript.behavior as javascript_behavior
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.store.state.schema import local_state_root
from ethos.repository.policy.code_subjects import observed_code_subjects
from tests.support.governed_repository import committed_source_repo

_ANSWER = {
    "answer.js": "export function answer() { return 42; }\n",
    "answer.test.js": 'import test from "node:test"; import {answer} from "./answer.js";\n'
    'test("answer", () => { if (answer() !== 42) throw Error("wrong"); });\n',
}


@pytest.mark.parametrize(
    ("scripts", "code"),
    [
        ({"pretest": "node setup.js", "test": "node --test answer.test.js"}, "recipe"),
        ({"test": "node --test answer.test.js && echo done"}, "recipe"),
        ({"test": "npm run unit"}, "recipe"),
        ({"test": ["node", "--test"]}, "recipe"),
        ({"test": 'node --test "answer.test.js'}, "recipe"),
        ({"test": "node --test answer.test.js", "test:coverage": ["c8"]}, "coverage_recipe"),
        (
            {"test": "node --test answer.test.js", "test:coverage": 'c8 "npm test'},
            "coverage_recipe",
        ),
        (
            {"test": "node --test answer.test.js", "test:coverage": "nyc npm test"},
            "coverage_recipe",
        ),
    ],
    ids=[
        "lifecycle",
        "shell",
        "launcher",
        "non-string",
        "quoting",
        "coverage-type",
        "coverage-quoting",
        "coverage-tool",
    ],
)
def test_unsupported_npm_recipes_are_refused_before_execution(
    tmp_path: Path, scripts: dict[str, object], code: str
) -> None:
    """Lifecycle hooks, shell composition and foreign tools are never silently skipped."""
    (tmp_path / "package.json").write_text(json.dumps({"type": "module", "scripts": scripts}))
    subjects = observed_code_subjects(tuple(_ANSWER))
    with pytest.raises(ValueError, match=f"^javascript_native_{code}_unsupported$"):
        javascript_behavior.behavior_observation(tmp_path, subjects, None, "/fixture/node", {})


def _answer_package(tmp_path: Path) -> Path:
    scripts = {"test": "node --test answer.test.js"}
    return committed_source_repo(
        tmp_path, {"package.json": json.dumps({"type": "module", "scripts": scripts}), **_ANSWER}
    )


@pytest.mark.parametrize(
    ("fault", "gaps"),
    [
        ("events", ["javascript_native_events_invalid", "javascript_native_selection_unknown"]),
        ("selection", ["javascript_native_events_invalid", "javascript_native_selection_invalid"]),
        (
            "missing-journal",
            ["javascript_native_events_incomplete", "javascript_native_selection_invalid"],
        ),
        ("timeout", ["javascript_native_attempt_timeout"]),
        ("process", ["process_spawn_failed"]),
    ],
)
def test_failed_native_attempts_are_retained_as_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, gaps: list[str]
) -> None:
    """Malformed journals, unknown selections and failed processes never prove behavior."""
    repo = _answer_package(tmp_path)
    journals: list[Path] = []

    def native(_cwd: Path, command: tuple[str, ...], *, env: dict[str, str], **_options: object):
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, 600, output=b"partial", stderr=b"late")
        if fault == "process":
            code = "process_spawn_failed"
            raise ProcessExecutionError(code, reason="fixture", command=command)
        if not command[1].endswith("selection.mjs"):
            journal = Path(env["NODE_V8_COVERAGE"]).parent / "journal.jsonl"
            journals.append(journal)
            if fault != "missing-journal":
                journal.write_text("not-json\n")
                assert journal.read_text() == "not-json\n"
            return subprocess.CompletedProcess(command, 0, "not-json\n", "")
        if fault == "events":
            return subprocess.CompletedProcess(command, 1, "", "native selection failed")
        selected = json.dumps({"selected_paths": ["other.js"]})
        return subprocess.CompletedProcess(command, 0, selected, "")

    monkeypatch.setattr(javascript_behavior, "run_command", native)
    subjects = observed_code_subjects(tuple(_ANSWER))
    report = javascript_behavior.behavior_observation(repo, subjects, None, "/fixture/node", {})
    assert (report["verdict"], report["required_gaps"]) == ("block", gaps)
    artifact = report["artifact"]
    assert isinstance(artifact, dict)
    assert Path(artifact["path"]).is_file()
    with ZipFile(artifact["path"]) as archive:
        assert ("journal.jsonl" in archive.namelist()) is (fault in {"events", "selection"})
        if fault in {"events", "selection"}:
            assert archive.read("journal.jsonl") == b"not-json\n"
    assert all(not journal.parent.exists() for journal in journals)


def test_interrupted_native_attempt_still_conserves_its_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An attempt interrupted outside the native protocol is retained before it propagates."""
    repo = _answer_package(tmp_path)

    def interrupted(*_args: object, **_options: object):
        message = "native attempt interrupted"
        raise OSError(message)

    monkeypatch.setattr(javascript_behavior, "run_command", interrupted)
    subjects = observed_code_subjects(tuple(_ANSWER))
    with pytest.raises(OSError, match="native attempt interrupted"):
        javascript_behavior.behavior_observation(repo, subjects, None, "/fixture/node", {})
    [artifact] = (local_state_root(repo) / "artifacts").glob("*.zip")
    with ZipFile(artifact) as archive:
        observation = json.loads(archive.read("observation.json"))
    assert observation["required_gaps"] == ["javascript_native_attempt_interrupted"]
