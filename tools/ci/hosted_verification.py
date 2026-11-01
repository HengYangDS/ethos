"""Bind one executed hosted proof of the checkout to a CI verification receipt.

The receipt records what a Forge observed for one exact head; it never satisfies
repository proof. A failed tool supply precedes proof, and stale evidence from an
earlier run is removed before either can be read.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from allure_pytest.utils import ParsedPytestNodeId

from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.runtime.filesystem import remove_owned_path
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from tools.ci.toolchain.environment import ProjectRuntime

PROVE = (
    *("uv", "run", "--frozen", "--offline", "--no-sync"),
    *("python", *PYTHON_FLAGS, "-m", "ethos.cli", "prove"),
    *("--host", "--execute", "--full"),
)
DIAGNOSTIC_LINES = 200
# The Python test gate's native output root; the shipped probe copies its attempt's reports here.
REPORTS = Path("build/evidence/quality/tests")
PROBE = "ethos.adapters.gates.python_quality:behavior_report"


def run(root: Path, head: str | None = None) -> int:
    """Prove head, defaulting to HEAD, write its receipt and return the exit status."""
    root = root.resolve()
    observed = subprocess.check_output(
        ("git", "rev-parse", "HEAD"), cwd=root, encoding="utf-8"
    ).strip()
    expected = head or observed
    out = root / "build/evidence/quality/proof"
    reports = root / REPORTS
    proof, diagnostics = out / "executed-proof.json", out / "executed-proof.stderr.log"
    out.mkdir(parents=True, exist_ok=True)
    stale = (
        proof,
        diagnostics,
        out / "hosted-verification.json",
        out / "hosted-verification.json.tmp",
    )
    for path in stale:
        path.unlink(missing_ok=True)
    remove_owned_path(reports)
    reports.mkdir(parents=True)
    supply_exit, proof_exit = _prove(root, expected, proof, diagnostics, reports)
    report, checks = _receipt(root, proof, expected, observed, proof_exit, supply_exit)
    summary = _report_tests(root, report, checks, supply_exit)
    receipt_exit = _publish(proof, report, checks, summary)
    if proof_exit or receipt_exit:
        lines = diagnostics.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            sys.stderr.write(f"ETHOS proof diagnostics (last {DIAGNOSTIC_LINES} lines):\n")
            sys.stderr.write("".join(f"{line}\n" for line in lines[-DIAGNOSTIC_LINES:]))
        return proof_exit or receipt_exit
    diagnostics.unlink(missing_ok=True)
    return 0


def _prove(
    root: Path, expected: str, proof: Path, diagnostics: Path, reports: Path
) -> tuple[int, int]:
    """Prepare the proof tools, then execute the full hosted proof of the expected head."""
    native = str(root / "tools/ci/toolchain/native.py")
    with diagnostics.open("wb") as stderr:
        supply = subprocess.run(
            (
                sys.executable,
                "-B",
                native,
                "--root",
                str(root),
                "--mise",
                "gitleaks",
                "scc",
                "syft",
                "vale",
            ),
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=stderr,
            check=False,
        )
        if supply.returncode:
            return supply.returncode, supply.returncode
        path = os.pathsep.join((supply.stdout.decode().strip(), os.environ.get("PATH", "")))
        with proof.open("wb") as stdout:
            completed = subprocess.run(
                (*PROVE, "--expect-head", expected, "--json"),
                cwd=root,
                stdout=stdout,
                stderr=stderr,
                env={**os.environ, "PATH": path, "ETHOS_NATIVE_OUTPUT_DIR": str(reports)},
                check=False,
            )
    return 0, completed.returncode


def _receipt(
    root: Path, proof: Path, expected: str, observed: str, proof_exit: int, supply_exit: int
) -> tuple[dict[str, Any], list[Any]]:
    """Accept only a complete executed host observation of the declared full gate set."""
    report: dict[str, Any] = {
        "kind": "ethos_hosted_verification_receipt",
        "verdict": "block",
        "satisfies_repository_proof": False,
        "expected_head": expected,
        "head": observed,
        "head_matches_expected": observed == expected,
        "process_exit_code": proof_exit,
        "supply_exit_code": supply_exit,
        "required_gaps": [],
    }
    checks: list[Any] = []
    try:
        policy = _policy(root, observed, supply_exit)
        raw = proof.read_bytes()
        observation = json.loads(raw)
        data, summary = observation["data"], observation["summary"]
        coordinates, checks = data["expected_head"], data["checks"]
        _require_check_objects(checks)
        gaps = list(policy.result_gaps(checks, source_tree=current_tree(root, observed)))
        valid = (
            proof_exit == 0
            and observed == expected
            and observation["verdict"] == "pass"
            and observation["state"] == "observed"
            and not observation["required_gaps"]
            and data["executed"] is True
            and data["boundary"] == summary["boundary"] == "host"
            and summary["proof_attestation_issued"] is False
            and data["attestation"] == {}
            and coordinates == {"expected": expected, "current": expected, "matches": True}
            and bool(checks)
            and summary["gate_count"] == len(checks)
            and not gaps
        )
        report.update(
            verdict="pass" if valid else "block",
            gate_count=len(checks),
            required_gaps=[*observation["required_gaps"], *gaps],
            expected_gate_count=len(policy.nodes),
            policy_digest=policy.digest,
            report_sha256=hashlib.sha256(raw).hexdigest(),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        report["required_gaps"] = (
            ["hosted_tool_supply_failed"]
            if supply_exit
            else [f"invalid_hosted_observation:{error}"]
        )
    if report["verdict"] != "pass" and not report["required_gaps"]:
        report["required_gaps"] = ["hosted_observation_binding_invalid"]
    return report, checks


def _policy(root: Path, observed: str, supply_exit: int) -> Any:
    """Resolve the full gate policy of the observed head once its tools were supplied."""
    if supply_exit:
        message = "hosted_tool_supply_failed"
        raise ValueError(message)
    policy = resolve_gate_policy(root, tree_ref=observed, full=True)
    if policy.gaps:
        message = "hosted_policy_invalid:" + ",".join(policy.gaps)
        raise ValueError(message)
    return policy


def _require_check_objects(checks: object) -> None:
    if not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks):
        message = "hosted_checks_invalid"
        raise ValueError(message)


def _report_tests(
    root: Path, report: dict[str, Any], checks: list[Any], supply_exit: int
) -> list[str]:
    """Record the probe's test and coverage evidence, render the Allure views; return lines."""
    lines: list[str] = []
    if supply_exit:
        return lines
    evidence = _probe_report(checks)
    tests, coverage = evidence.get("tests"), evidence.get("coverage")
    if isinstance(tests, dict):
        report["tests"] = tests
        lines.append(
            f"Tests: {tests['total']}; failures: {tests['failures']}; "
            f"errors: {tests['errors']}; skipped: {tests['skipped']}"
        )
        if tests["failures"] or tests["errors"] or tests["skipped"] >= tests["total"]:
            report["required_gaps"].append("hosted_test_report_failed")
    else:
        report["required_gaps"].append("hosted_test_report_invalid")
        lines.append("Tests: unavailable")
    if isinstance(coverage, dict):
        report["coverage"] = coverage
        lines.append(f"Coverage: {coverage['combined_percent']:.2f}% combined statements/branches")
    else:
        report["required_gaps"].append("hosted_coverage_report_invalid")
        lines.append("Coverage: unavailable")
    try:
        _render_allure(root, root / REPORTS)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        report["required_gaps"].append(f"hosted_allure_report_invalid:{error}")
    if report["required_gaps"]:
        report["verdict"] = "block"
    return lines


def _probe_report(checks: list[Any]) -> dict[str, Any]:
    """Read the shipped behavior probe's report from the executed proof's provider rows."""
    for check in checks:
        try:
            providers = json.loads(check["stdout"])["providers"]
        except (KeyError, TypeError, ValueError):
            continue
        for item in providers if isinstance(providers, list) else ():
            if isinstance(item, dict) and item.get("provider") == PROBE:
                report = item.get("report")
                return report if isinstance(report, dict) else {}
    return {}


def _render_allure(root: Path, reports: Path) -> None:
    """Refuse Allure results whose case identities differ from the execution's, then render."""
    results = reports / "allure/results"
    named = Counter(
        json.loads(path.read_text(encoding="utf-8"))["fullName"]
        for path in results.glob("*-result.json")
    )
    events = (reports / "pytest/events.jsonl").read_text(encoding="utf-8").splitlines()
    executed = Counter(
        _allure_name(event["nodeid"])
        for event in map(json.loads, events)
        if event.get("$report_type") == "TestReport" and event.get("when") == "setup"
    )
    if not executed or named != executed:
        message = "allure_identities_differ"
        raise ValueError(message)
    runtime, output = ProjectRuntime.discover(root), reports / "allure/agent"
    cli = runtime.node_package_supply() / "allure/cli.js"
    command = (str(runtime.node_executable()), str(cli), "agent", "inspect", "--cwd")
    result = run_command(
        root,
        (
            *command,
            str(reports / "allure"),
            "--output",
            str(output),
            "--report",
            "awesome",
            str(results),
        ),
        timeout=180,
    )
    manifest = output / "manifest/human-report.json"
    if (
        result.returncode
        or json.loads(manifest.read_text(encoding="utf-8"))["status"] != "generated"
    ):
        message = f"allure_render_failed:{result.returncode}"
        raise RuntimeError(message)


def _allure_name(nodeid: str) -> str:
    """Name a case as allure-pytest's `fullName` does: package, classes and function."""
    parsed = ParsedPytestNodeId(nodeid)
    classes = "".join(f".{name}" for name in parsed.class_names)
    return f"{parsed.package}{classes}#{parsed.test_function}"


def _publish(proof: Path, report: dict[str, Any], checks: list[Any], summary: list[str]) -> int:
    """Write the Markdown summary and the receipt, print the receipt and return its status."""
    lines = [
        "## ETHOS verification",
        f"Source: `{report['head']}`; expected: `{report['expected_head']}`",
        f"Hosted observation: **{report['verdict']}**; process exit: {report['process_exit_code']}",
        *summary,
    ]
    if report["required_gaps"]:
        lines.append("Required gaps: " + ", ".join(report["required_gaps"]))
    rows = ["| Gate | Verdict | Exit | Seconds |", "| --- | --- | --- | --- |"]
    keys = ("action_id", "verdict", "exit_code", "duration_seconds")
    for check in checks if isinstance(checks, list) else []:
        if isinstance(check, dict):
            cells = (
                str(check.get(key, "unavailable")).replace("|", "\\|").replace("\n", " ")
                for key in keys
            )
            rows.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "\n".join(rows),
            (
                "Raw diagnostics and reports are retained artifacts; "
                "this observation grants no repository authority."
            ),
        ]
    )
    markdown = "\n\n".join(lines) + "\n"
    proof.with_name("hosted-verification.md").write_text(markdown, encoding="utf-8")
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        try:
            with Path(summary_path).open("a", encoding="utf-8") as stream:
                stream.write(markdown)
        except OSError as error:
            sys.stderr.write(f"test_summary_unavailable:{error}\n")
    rendered = json.dumps(report, sort_keys=True)
    receipt = proof.with_name("hosted-verification.json")
    pending = receipt.with_suffix(".json.tmp")
    pending.write_text(rendered + "\n", encoding="utf-8")
    pending.replace(receipt)
    sys.stdout.write(rendered + "\n")
    return int(report["verdict"] != "pass")
