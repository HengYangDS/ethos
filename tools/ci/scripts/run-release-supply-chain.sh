#!/usr/bin/env bash
# Generate an SPDX 2.3 JSON SBOM for the exact built wheel. This local gate does
# not emit provenance, sign an attestation, publish, or claim hosted success.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "${repo_root}"

config=".config/release/supply-chain.toml"
artifact_glob=""
output=""
sbom=""
tool_version=""
eval "$(python - "${config}" <<'PY'
import shlex, sys, tomllib
from pathlib import Path
policy = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for key in ("artifact_glob", "output", "sbom", "tool_version"):
    print(f"{key}={shlex.quote(str(policy[key]))}")
PY
)"

tools/ci/scripts/install-syft.sh >/dev/null
observed_version="$(syft version -o json | python -c 'import json,sys; print(json.load(sys.stdin)["version"])')"
if [[ "${observed_version}" != "${tool_version}" ]]; then
  printf 'expected syft %s, observed %s\n' "${tool_version}" "${observed_version}" >&2
  exit 1
fi

shopt -s nullglob
artifacts=()
while IFS= read -r artifact_path; do
  artifacts+=("${artifact_path}")
done < <(compgen -G "${artifact_glob}" || true)
if [[ "${#artifacts[@]}" -ne 1 ]]; then
  printf 'expected exactly one artifact matching %s\n' "${artifact_glob}" >&2
  exit 1
fi
artifact="${artifacts[0]}"
mkdir -p "$(dirname "${sbom}")" "$(dirname "${output}")"
syft scan "file:${artifact}" --quiet --output "spdx-json=${sbom}"

HEAD="$(git rev-parse HEAD)" ARTIFACT="${artifact}" OUTPUT="${output}" SBOM="${sbom}" \
  SYFT_VERSION="${observed_version}" python - <<'PY'
import hashlib, json, os
from datetime import UTC, datetime
from pathlib import Path

artifact, sbom, output = map(Path, (os.environ["ARTIFACT"], os.environ["SBOM"], os.environ["OUTPUT"]))
document = json.loads(sbom.read_text(encoding="utf-8"))
if document.get("spdxVersion") != "SPDX-2.3":
    raise SystemExit("syft output is not SPDX 2.3")
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
payload = {
    "schema_version": 1,
    "kind": "ethos_release_supply_chain_evidence",
    "verdict": "pass",
    "head": os.environ["HEAD"],
    "generated_at": datetime.now(UTC).isoformat(),
    "artifact": {"path": artifact.as_posix(), "sha256": digest(artifact)},
    "sbom": {"path": sbom.as_posix(), "sha256": digest(sbom), "format": "SPDX-2.3"},
    "generator": {"tool": "syft", "version": os.environ["SYFT_VERSION"]},
    "not_claimed": ["provenance", "signature", "SLSA level", "hosted CI", "publication"],
}
rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
output.write_text(rendered, encoding="utf-8")
print(rendered, end="")
PY
