#!/usr/bin/env bash
# Observe hosted gates without local lifecycle authority; bind the exact object.
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != 1 ]]; then exec "${dir}/with-python-runtime.sh" -- uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"; fi
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
[[ $# -le 1 ]] || {
	echo "usage: $0 [expected-head]" >&2
	exit 2
}
head="${1:-$(git rev-parse HEAD)}"
out="${ETHOS_PROOF_EVIDENCE_DIR:-build/evidence/quality/proof}"
receipt="${out}/executed-proof.json"
stderr="${out}/executed-proof.stderr.log"
reports="${ETHOS_TEST_EVIDENCE_DIR:-build/evidence/quality/tests}"
mkdir -p "${out}"
rm -f "${receipt}" "${stderr}" "${out}/hosted-verification.json" "${out}/hosted-verification.json.tmp"
rm -f -- "${reports}/pytest"/junit*.xml "${reports}/coverage/coverage.xml" "${reports}/coverage/head.txt"
set +e
supply_directory="$(python "${dir}/../toolchain/native.py" --root "$PWD" gitleaks scc syft 2>"${stderr}")"
supply_status=$?
proof_status=${supply_status}
if [[ ${supply_status} -eq 0 ]]; then
	PATH="${supply_directory}:${PATH}" uv run --frozen --offline ethos prove --host --execute --full --expect-head "${head}" --json >"${receipt}" 2>>"${stderr}"
	proof_status=$?
fi
python3 - "${receipt}" "${head}" "$(git rev-parse HEAD)" "${proof_status}" "${supply_status}" <<'PY'
import hashlib, json, os, sys
import xml.etree.ElementTree as ET
from pathlib import Path
path, expected, observed, exit_code, supply_exit = Path(sys.argv[1]), *sys.argv[2:]
report = {"kind": "ethos_hosted_verification_receipt", "verdict": "block",
          "satisfies_repository_proof": False, "expected_head": expected,
          "head": observed, "head_matches_expected": observed == expected,
          "process_exit_code": int(exit_code), "supply_exit_code": int(supply_exit), "required_gaps": []}
checks = []
try:
    if supply_exit != "0":
        raise ValueError("hosted_tool_supply_failed")
    from ethos.adapters.repo.gate_policy import resolve_gate_policy
    policy = resolve_gate_policy(Path.cwd(), tree_ref=observed, full=True)
    if policy.gaps:
        raise ValueError("hosted_policy_invalid:" + ",".join(policy.gaps))
    raw = path.read_bytes()
    proof = json.loads(raw)
    data, summary = proof["data"], proof["summary"]
    coordinates, checks = data["expected_head"], data["checks"]
    if not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks):
        raise ValueError("hosted_checks_invalid")
    gaps = list(policy.result_gaps(checks))
    valid = (
        exit_code == "0" and observed == expected
        and proof["verdict"] == "pass" and proof["state"] == "observed"
        and not proof["required_gaps"] and data["executed"] is True
        and data["boundary"] == summary["boundary"] == "host"
        and summary["proof_attestation_issued"] is False and data["attestation"] == {}
        and coordinates == {"expected": expected, "current": expected, "matches": True}
        and isinstance(checks, list) and bool(checks) and summary["gate_count"] == len(checks)
        and not gaps
    )
    report.update(verdict="pass" if valid else "block", gate_count=len(checks),
                  required_gaps=[*proof["required_gaps"], *gaps],
                  expected_gate_count=len(policy.nodes), policy_digest=policy.digest,
                  report_sha256=hashlib.sha256(raw).hexdigest())
except (OSError, ValueError, KeyError, TypeError) as error:
    report["required_gaps"] = (["hosted_tool_supply_failed"] if supply_exit != "0"
                               else [f"invalid_hosted_observation:{error}"])
if report["verdict"] != "pass" and not report["required_gaps"]:
    report["required_gaps"] = ["hosted_observation_binding_invalid"]
evidence = Path(os.environ.get("ETHOS_TEST_EVIDENCE_DIR", "build/evidence/quality/tests"))
report_lines = []
if supply_exit == "0":
    try:
        files = sorted((evidence / "pytest").glob("junit*.xml"))
        if not files:
            raise ValueError("missing JUnit")
        suites = [ET.parse(file).getroot() for file in files]
        if any(suite.tag not in {"testsuite", "testsuites"} for suite in suites):
            raise ValueError("invalid JUnit root")
        cases = [case for suite in suites for case in suite.iter("testcase")]
        if not cases:
            raise ValueError("empty JUnit")
        failures, errors, skipped = (sum(case.find(tag) is not None for case in cases)
                                     for tag in ("failure", "error", "skipped"))
        report["tests"] = dict(total=len(cases), failures=failures, errors=errors, skipped=skipped)
        report_lines.append(f"Tests: {len(cases)}; failures: {failures}; errors: {errors}; skipped: {skipped}")
        if failures or errors or any(int(suite.get(key, "0")) for root in suites
                                    for suite in root.iter() if suite.tag in {"testsuite", "testsuites"}
                                    for key in ("failures", "errors")):
            report["required_gaps"].append("hosted_test_report_failed")
    except (OSError, ValueError, ET.ParseError) as error:
        report["required_gaps"].append("hosted_test_report_invalid")
        report_lines.append(f"Tests: unavailable ({type(error).__name__})")
    try:
        coverage_root = ET.parse(evidence / "coverage/coverage.xml").getroot()
        coverage = coverage_root.attrib
        covered, total = ((int(coverage[f"{name}-covered"]), int(coverage[f"{name}-valid"]))
                          for name in ("lines", "branches"))
        if coverage_root.tag != "coverage" or any(not 0 <= hit <= count for hit, count in (covered, total)):
            raise ValueError("invalid coverage counts")
        hit, count = covered[0] + total[0], covered[1] + total[1]
        if count == 0:
            raise ValueError("empty coverage")
        report["coverage"] = dict(covered=hit, total=count, combined_percent=100 * hit / count)
        report_lines.append(f"Coverage: {100 * hit / count:.2f}% combined statements/branches")
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        report["required_gaps"].append("hosted_coverage_report_invalid")
        report_lines.append(f"Coverage: unavailable ({type(error).__name__})")
if report["required_gaps"]:
    report["verdict"] = "block"
lines = ["## ETHOS verification", f"Source: `{observed}`; expected: `{expected}`",
         f"Hosted observation: **{report['verdict']}**; process exit: {exit_code}", *report_lines]
if report["required_gaps"]:
    lines.append("Required gaps: " + ", ".join(report["required_gaps"]))
rows = ["| Gate | Verdict | Exit | Seconds |", "| --- | --- | --- | --- |"]
for check in checks if isinstance(checks, list) else []:
    if isinstance(check, dict):
        rows.append("| " + " | ".join(str(check.get(key, "unavailable")).replace("|", "\\|").replace("\n", " ")
                    for key in ("action_id", "verdict", "exit_code", "duration_seconds")) + " |")
lines.extend(["\n".join(rows), "Raw diagnostics and reports are retained artifacts; this observation grants no repository authority."])
markdown = "\n\n".join(lines) + "\n"
path.with_name("hosted-verification.md").write_text(markdown, encoding="utf-8")
if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
    try:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write(markdown)
    except OSError as error:
        print(f"test_summary_unavailable:{error}", file=sys.stderr)
rendered = json.dumps(report, sort_keys=True)
receipt = path.with_name("hosted-verification.json")
pending = receipt.with_suffix(".json.tmp")
pending.write_text(rendered + "\n", encoding="utf-8")
pending.replace(receipt)
print(rendered)
verdict = report["verdict"]
raise SystemExit(verdict != "pass")
PY
receipt_status=$?
set -e
if [[ ${proof_status} -ne 0 || ${receipt_status} -ne 0 ]]; then
	[[ ! -s "${stderr}" ]] || {
		echo "ETHOS proof diagnostics (last 200 lines):" >&2
		tail -n 200 "${stderr}" >&2
	}
	((proof_status)) && exit "${proof_status}"
	exit "${receipt_status}"
fi
rm -f "${stderr}"
