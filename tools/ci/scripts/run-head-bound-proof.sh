#!/usr/bin/env bash
# Execute proof into generated evidence and print its head-bound receipt.
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != 1 ]]; then
  exec "${dir}/with-python-runtime.sh" -- uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
[[ $# -le 1 ]] || { echo "usage: $0 [expected-head]" >&2; exit 2; }
head="${1:-$(git rev-parse HEAD)}"
out="${ETHOS_PROOF_EVIDENCE_DIR:-build/evidence/quality/proof}"
receipt="${out}/executed-proof.json"
stderr="${out}/executed-proof.stderr.log"
mkdir -p "${out}"
rm -f "${receipt}" "${stderr}"
set +e
uv run --package ethos ethos prove --execute --expect-head "${head}" --json >"${receipt}" 2>"${stderr}"
proof_status=$?
set -e
set +e
python3 - "${receipt}" "${head}" "${proof_status}" <<'PY'
import hashlib,json,sys
from pathlib import Path
path, expected_head, proof_status = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
try:
    proof = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    print(json.dumps({"kind": "ethos_head_bound_proof_receipt", "ok": False, "state": "invalid_receipt", "expected_head": expected_head, "proof_exit_code": proof_status, "error": str(error)}, sort_keys=True))
    raise SystemExit(1)
summary, data = proof.get("summary"), proof.get("data")
bound = data.get("expected_head") if isinstance(data, dict) else {}
ok = proof.get("ok") is True and proof_status == 0 and isinstance(bound, dict) and bound.get("ok") is True
print(json.dumps({"kind": "ethos_head_bound_proof_receipt", "ok": ok, "state": proof.get("state", "unknown"), "head": bound.get("current", "") if isinstance(bound, dict) else "", "expected_head": expected_head, "head_matches_expected": bound.get("ok") is True if isinstance(bound, dict) else False, "gate_count": summary.get("gate_count", 0) if isinstance(summary, dict) else 0, "evidence_digest": summary.get("evidence_digest", "") if isinstance(summary, dict) else "", "required_gap_count": len(proof.get("required_gaps", [])), "proof_exit_code": proof_status, "receipt": path.as_posix(), "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, sort_keys=True))
raise SystemExit(0 if ok else 1)
PY
receipt_status=$?
set -e
if [[ ${proof_status} -ne 0 || ${receipt_status} -ne 0 ]]; then
  [[ ! -s "${stderr}" ]] || { echo "ETHOS proof diagnostics (last 200 lines):" >&2; tail -n 200 "${stderr}" >&2; }
  (( proof_status )) && exit "${proof_status}"
  exit "${receipt_status}"
fi
rm -f "${stderr}"
