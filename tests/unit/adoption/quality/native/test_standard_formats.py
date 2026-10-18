"""Judge tool-neutral native reports for any language without replaying the tools."""

from __future__ import annotations

import json
import sys
import tomllib
from typing import TYPE_CHECKING
from typing import cast

import pytest
import tomli_w

import ethos.adapters.gates.code_quality as code_quality
from ethos.adapters.gates.formatting import prepare_source_format
from ethos.adapters.gates.native.attempt import native_attempt
from ethos.adapters.gates.native.attempt import retained_execution
from ethos.adapters.gates.verification import NativeExecution
from ethos.contracts.gates import Gate
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_quality_profile
from tests.support.proof import run_quality_proof

if TYPE_CHECKING:
    from pathlib import Path

# The native command writes reports chosen by each case into the attempt's output root.
_WRITER = (
    "import json, os, pathlib, sys\n"
    "root = pathlib.Path(os.environ['ETHOS_NATIVE_OUTPUT_DIR'])\n"
    "for name, text in json.loads(sys.argv[1]).items():\n"
    "    (root / name).write_text(text)\n"
)
_SCRIPT = "#!/bin/sh\nprintf '%s\\n' ready\n"


def _junit(*, failed: bool = False) -> str:
    outcome = "<failure/>" if failed else ""
    case = f'<testcase classname="run" name="ready">{outcome}</testcase>'
    return f'<testsuite tests="1">{case}</testsuite>'


def _cobertura(root: Path, hits: int) -> str:
    """Mirror kcov: line counts, a constant covered branch value and no branch total."""
    return (
        '<coverage lines-covered="1" lines-valid="1" branches-covered="1.0">'
        f"<sources><source>{root}/</source></sources><packages><package><classes>"
        f'<class filename="bin/run.sh"><lines><line number="2" hits="{hits}"/></lines></class>'
        "</classes></package></packages></coverage>"
    )


def _sarif(root: Path, *, inventory: bool = True, finding: bool = False) -> str:
    result = {
        "ruleId": "SC2086",
        "level": "warning",
        "message": {"text": "Double quote to prevent globbing."},
        "locations": [
            {"physicalLocation": {"artifactLocation": {"uri": f"file://{root}/bin/run.sh"}}}
        ],
    }
    run: dict[str, object] = {
        "tool": {"driver": {"name": "linter"}},
        "results": [result] if finding else [],
    }
    if inventory:
        run["artifacts"] = [
            {"location": {"uri": path}, "roles": ["analysisTarget"]}
            for path in ("bin/run.sh", "tests/run_test.sh")
        ]
    return json.dumps({"version": "2.1.0", "runs": [run]})


def _execution(root: Path, outcome: str) -> NativeExecution:
    """Run one native attempt whose reports describe the committed scripts."""
    resolved = root.resolve()
    reports = {
        "tests.xml": _junit(failed=outcome == "failed"),
        "coverage.xml": _cobertura(resolved, 0 if outcome == "unexecuted" else 1),
        "coverage.lcov": "SF:bin/run.sh\nDA:2,1\nend_of_record\n",
        "lint.sarif": _sarif(
            resolved, inventory=outcome != "unscoped", finding=outcome == "finding"
        ),
    }
    coverage = "coverage.lcov" if outcome == "lcov" else "coverage.xml"
    outputs = [
        {"path": "tests.xml", "format": "junit-xml", "sessions": ("tests",)},
        {
            "path": coverage,
            "format": "lcov" if outcome == "lcov" else "cobertura-xml",
            "sessions": ("untested" if outcome == "untested" else "tests",),
        },
        {"path": "lint.sarif", "format": "sarif", "sessions": ("lint",)},
    ]
    gate = Gate.model_validate(
        {
            "id": "native-scripts",
            "kind": "test",
            "command": (sys.executable, "-c", _WRITER, json.dumps(reports)),
            "verification_providers": (
                "ethos.adapters.gates.code_quality:behavior_report",
                "ethos.adapters.gates.code_quality:static_report",
            ),
            "native_outputs": tuple(outputs),
        }
    )
    completed, evidence = native_attempt(root, gate, gate.command, timeout=45)
    return retained_execution(
        NativeExecution(
            gate_execution_identity(gate),
            tuple(completed.args),
            resolved,
            completed.returncode,
            completed.stdout,
            completed.stderr,
            executable=gate.command[0],
            evidence=evidence,
        )
    )


@pytest.mark.parametrize(
    ("outcome", "behavior", "static"),
    [
        ("pass", "", ""),
        ("lcov", "", ""),
        ("unexecuted", "quality_behavior_native_source_unexercised:bin/run.sh", ""),
        ("failed", "quality_behavior_native_tests_failed", ""),
        ("untested", "quality_behavior_native_coverage_untested", ""),
        ("finding", "", "quality_static-analysis_native_static_findings:SC2086:bin/run.sh"),
        ("unscoped", "", "quality_static-analysis_native_static_scope_unknown:lint.sarif"),
    ],
)
def test_script_reports_are_judged_by_property(
    tmp_path: Path, outcome: str, behavior: str, static: str
) -> None:
    """Tests, executed lines and a clean inventoried scan claim scripts without a Nox report."""
    repo = committed_source_repo(
        tmp_path, {"bin/run.sh": _SCRIPT, "tests/run_test.sh": "#!/bin/sh\n./bin/run.sh\n"}
    )
    execution = _execution(repo, outcome)
    reports = {
        "behavior": code_quality.behavior_report(repo, execution=execution),
        "static-analysis": code_quality.static_report(repo, execution=execution),
    }
    for axis, gap in (("behavior", behavior), ("static-analysis", static)):
        report = reports[axis]
        assert report["required_gaps"] == ([gap] if gap else []), report
        if not gap:
            assert cast("dict[str, object]", report["native"])["sessions"] == []
            evidence = cast("dict[str, object]", report["quality_evidence"])
            assert evidence["selected_paths"] == (
                ["bin/run.sh"] if axis == "behavior" else ["bin/run.sh", "tests/run_test.sh"]
            )


def test_ethos_checks_claim_only_the_languages_they_judge(tmp_path: Path) -> None:
    """A language without an ETHOS check stays unclaimed rather than blocking the gate."""
    repo = committed_source_repo(
        tmp_path,
        {".gitattributes": "main.rs ethos-role=code\n", "bin/run.sh": _SCRIPT, "main.rs": "\n"},
    )
    static = code_quality.static_report(repo)
    assert static["verdict"] == "pass", static
    assert cast("dict[str, object]", static["quality_evidence"])["selected_paths"] == ["bin/run.sh"]
    assert static["unclaimed_paths"] == ["main.rs"]
    behavior = code_quality.behavior_report(repo)
    assert behavior["required_gaps"] == ["quality_behavior_native_language_unsupported:script"]


@pytest.mark.parametrize("covered", [("bin/run.sh", "bin/other.sh"), ("bin/run.sh",)])
def test_public_proof_joins_native_script_behavior_with_ethos_static(
    tmp_path: Path, covered: tuple[str, ...]
) -> None:
    """Native script evidence and ETHOS's own check discharge both axes only when complete."""
    repo = init_git_repo(tmp_path / "adopter")
    declare_quality_profile(repo)
    for name in ("bin/run.sh", "bin/other.sh"):
        script = repo / name
        script.parent.mkdir(exist_ok=True)
        script.write_text(_SCRIPT, encoding="utf-8")
        script.chmod(0o755)
    lcov = "".join(f"SF:{name}\nDA:2,1\nend_of_record\n" for name in covered)
    profile = repo / ".ethos/profile.toml"
    declaration = tomllib.loads(profile.read_text(encoding="utf-8"))
    gate = declaration["proof"]["gates"][0]
    gate["verification_providers"] = gate.pop("providers")
    gate["command"] = [
        sys.executable,
        "-c",
        _WRITER,
        json.dumps({"tests.xml": _junit(), "coverage.lcov": lcov}),
    ]
    gate["native_outputs"] = [
        {"path": "tests.xml", "format": "junit-xml", "sessions": ["scripts"]},
        {"path": "coverage.lcov", "format": "lcov", "sessions": ["scripts"]},
    ]
    profile.write_text(tomli_w.dumps(declaration), encoding="utf-8")
    for item in prepare_source_format(repo, paths=(".ethos/profile.toml",)):
        (repo / item.path).write_bytes(item.after)
    head = commit_fixture(repo, "measure script behavior with native reports")
    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)
    if len(covered) == 2:
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
    else:
        assert result.returncode != 0
        assert "quality_obligation_unproven:behavior" in payload["required_gaps"]
