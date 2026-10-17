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
from pathlib import Path
from typing import Any

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tree
from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import junit_report

PROVE = (
    *("uv", "run", "--frozen", "--offline", "python", "-B", "-I", "-m", "ethos.cli", "prove"),
    *("--host", "--execute", "--full"),
)
DIAGNOSTIC_LINES = 200


def run(root: Path, head: str | None = None) -> int:
    """Prove head, defaulting to HEAD, write its receipt and return the exit status."""
    root = root.resolve()
    observed = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()
    expected = head or observed
    out = root / "build/evidence/quality/proof"
    reports = root / os.environ.get("ETHOS_TEST_EVIDENCE_DIR", "build/evidence/quality/tests")
    proof, diagnostics = out / "executed-proof.json", out / "executed-proof.stderr.log"
    out.mkdir(parents=True, exist_ok=True)
    stale = (
        proof,
        diagnostics,
        out / "hosted-verification.json",
        out / "hosted-verification.json.tmp",
    )
    for path in (*stale, *(reports / "pytest").glob("junit*.xml")):
        path.unlink(missing_ok=True)
    for name in ("coverage.xml", "head.txt"):
        (reports / "coverage" / name).unlink(missing_ok=True)
    supply_exit, proof_exit = _prove(root, expected, proof, diagnostics)
    report, checks = _receipt(root, proof, expected, observed, proof_exit, supply_exit)
    summary = _report_tests(report, reports, supply_exit)
    receipt_exit = _publish(proof, report, checks, summary)
    if proof_exit or receipt_exit:
        lines = diagnostics.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            sys.stderr.write(f"ETHOS proof diagnostics (last {DIAGNOSTIC_LINES} lines):\n")
            sys.stderr.write("".join(f"{line}\n" for line in lines[-DIAGNOSTIC_LINES:]))
        return proof_exit or receipt_exit
    diagnostics.unlink(missing_ok=True)
    return 0


def _prove(root: Path, expected: str, proof: Path, diagnostics: Path) -> tuple[int, int]:
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
                env={**os.environ, "PATH": path},
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


def _report_tests(report: dict[str, Any], evidence: Path, supply_exit: int) -> list[str]:
    """Record the test and coverage reports the executed proof produced; return their lines."""
    lines: list[str] = []
    if not supply_exit:
        try:
            tests, failed = junit_report(sorted((evidence / "pytest").glob("junit*.xml")))
            report["tests"] = tests
            lines.append(
                f"Tests: {tests['total']}; failures: {tests['failures']}; "
                f"errors: {tests['errors']}; skipped: {tests['skipped']}"
            )
            if failed:
                report["required_gaps"].append("hosted_test_report_failed")
        except (OSError, ValueError) as error:
            reason = f":{error}" if isinstance(error, ValueError) else ""
            report["required_gaps"].append(f"hosted_test_report_invalid{reason}")
            lines.append(f"Tests: unavailable ({type(error).__name__})")
        try:
            coverage = coverage_report(evidence / "coverage/coverage.xml")
            report["coverage"] = coverage
            lines.append(
                f"Coverage: {coverage['combined_percent']:.2f}% combined statements/branches"
            )
        except (OSError, ValueError) as error:
            report["required_gaps"].append("hosted_coverage_report_invalid")
            lines.append(f"Coverage: unavailable ({type(error).__name__})")
    if report["required_gaps"]:
        report["verdict"] = "block"
    return lines


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
