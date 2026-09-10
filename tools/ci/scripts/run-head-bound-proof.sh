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
rm -f "${receipt}" "${stderr}"
rm -f -- "${reports}/pytest"/junit*.xml "${reports}/coverage/coverage.xml" "${reports}/coverage/head.txt"
set +e
uv run --frozen --offline ethos prove --host --execute --expect-head "${head}" --json >"${receipt}" 2>"${stderr}"
proof_status=$?
python3 - "${receipt}" "${head}" "$(git rev-parse HEAD)" "${proof_status}" <<'PY'
import hashlib, json, os, sys
import xml.etree.ElementTree as ET
from pathlib import Path
path, expected, observed, exit_code = Path(sys.argv[1]), *sys.argv[2:]
report = {"kind": "ethos_hosted_verification_receipt", "verdict": "block",
          "satisfies_repository_proof": False, "expected_head": expected,
          "head": observed, "head_matches_expected": observed == expected,
          "process_exit_code": int(exit_code), "required_gaps": []}
try:
    raw = path.read_bytes()
    proof = json.loads(raw)
    data, summary = proof["data"], proof["summary"]
    coordinates, checks = data["expected_head"], data["checks"]
    valid = (
        exit_code == "0" and observed == expected
        and proof["verdict"] == "pass" and proof["state"] == "observed"
        and not proof["required_gaps"] and data["executed"] is True
        and data["boundary"] == summary["boundary"] == "host"
        and summary["proof_attestation_issued"] is False and data["attestation"] == {}
        and coordinates == {"expected": expected, "current": expected, "matches": True}
        and isinstance(checks, list) and bool(checks) and summary["gate_count"] == len(checks)
        and {"unit-architecture", "coverage-floor"} <= {check["action_id"] for check in checks}
        and all(check["verdict"] == "pass" and check["exit_code"] == 0 for check in checks)
    )
    report.update(verdict="pass" if valid else "block", gate_count=len(checks),
                  required_gaps=proof["required_gaps"], report_sha256=hashlib.sha256(raw).hexdigest())
except (OSError, ValueError, KeyError, TypeError) as error:
    report["required_gaps"] = [f"invalid_hosted_observation:{error}"]
if report["verdict"] != "pass" and not report["required_gaps"]:
    report["required_gaps"] = ["hosted_observation_binding_invalid"]
if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
    evidence = Path(os.environ.get("ETHOS_TEST_EVIDENCE_DIR", "build/evidence/quality/tests"))
    lines = ["## ETHOS verification", f"Source: `{observed}`; expected: `{expected}`",
             f"Hosted observation: **{report['verdict']}**; process exit: {exit_code}"]
    try:
        files = sorted((evidence / "pytest").glob("junit*.xml"))
        if not files:
            raise ValueError("missing JUnit")
        cases = [case for file in files for case in ET.parse(file).iter("testcase")]
        if not cases:
            raise ValueError("empty JUnit")
        failures, errors, skipped = (sum(case.find(tag) is not None for case in cases)
                                     for tag in ("failure", "error", "skipped"))
        lines.append(f"Tests: {len(cases)}; failures: {failures}; errors: {errors}; skipped: {skipped}")
    except (OSError, ValueError, ET.ParseError) as error:
        lines.append(f"Tests: unavailable ({type(error).__name__})")
    try:
        coverage = ET.parse(evidence / "coverage/coverage.xml").getroot().attrib
        hit = sum(int(coverage[key]) for key in ("lines-covered", "branches-covered"))
        total = sum(int(coverage[key]) for key in ("lines-valid", "branches-valid"))
        if not 0 <= hit <= total or total == 0:
            raise ValueError("invalid coverage counts")
        lines.append(f"Coverage: {100 * hit / total:.2f}% combined statements/branches")
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        lines.append(f"Coverage: unavailable ({type(error).__name__})")
    lines.append("JUnit, coverage and exact diagnostics are in the job artifacts; this summary grants no authority.")
    try:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write("\n\n".join(lines) + "\n")
    except OSError as error:
        print(f"test_summary_unavailable:{error}", file=sys.stderr)
print(json.dumps(report, sort_keys=True))
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
