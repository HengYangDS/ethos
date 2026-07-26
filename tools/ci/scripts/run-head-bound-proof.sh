#!/usr/bin/env bash
# Execute proof into generated evidence and print its head-bound receipt.
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != 1 ]]; then exec "${dir}/with-python-runtime.sh" -- uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"; fi
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
[[ $# -le 1 ]] || { echo "usage: $0 [expected-head]" >&2; exit 2; }
head="${1:-$(git rev-parse HEAD)}"; out="${ETHOS_PROOF_EVIDENCE_DIR:-build/evidence/quality/proof}"; readiness="${ETHOS_READINESS_EVIDENCE_DIR:-build/evidence/quality/readiness}"
receipt="${out}/executed-proof.json"; stderr="${out}/executed-proof.stderr.log"; audit="${readiness}/audit.json"; report="${readiness}/report.json"
mkdir -p "${out}" "${readiness}"; rm -f "${receipt}" "${stderr}" "${audit}" "${report}"
uv run ethos audit --json >"${audit}"
set +e; uv run ethos prove --execute --expect-head "${head}" --json >"${receipt}" 2>"${stderr}"; proof_status=$?; set -e
uv run ethos report --json >"${report}"
set +e
python3 - "${audit}" "${report}" "${receipt}" <<'PY'
import hashlib, json, sys
from pathlib import Path
paths = tuple(map(Path, sys.argv[1:4]))
try: audit, report, proof = (json.loads(path.read_text()) for path in paths)
except (OSError, json.JSONDecodeError) as error: raise SystemExit(f"invalid readiness receipt: {error}") from error
data = proof.get("data", {}); head = data.get("expected_head", {}) if isinstance(data, dict) else {}; summary = proof.get("summary", {}); ok = all(item.get("ok") is True for item in (audit, report, proof))
print(json.dumps({"kind": "ethos_hosted_readiness_receipt", "ok": ok, "audit_state": audit.get("state", ""), "report_state": report.get("state", ""), "proof_state": proof.get("state", ""), "head": head.get("current", ""), "head_matches_expected": head.get("ok", False), "proof_gate_count": summary.get("gate_count", 0), "proof_evidence_digest": summary.get("evidence_digest", ""), "reports": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}, sort_keys=True))
raise SystemExit(not ok)
PY
receipt_status=$?; set -e
if [[ ${proof_status} -ne 0 || ${receipt_status} -ne 0 ]]; then [[ ! -s "${stderr}" ]] || { echo "ETHOS proof diagnostics (last 200 lines):" >&2; tail -n 200 "${stderr}" >&2; }; (( proof_status )) && exit "${proof_status}"; exit "${receipt_status}"; fi
rm -f "${stderr}"
