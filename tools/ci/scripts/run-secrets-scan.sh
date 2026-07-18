#!/usr/bin/env bash
# Run the secret-scanning gate. Secret policy lives in the root .gitleaks.toml
# (gitleaks requires the config at a git-discoverable location); the concern is
# registered under .config/checks/secrets/.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

"${script_dir}/install-gitleaks.sh"

report_dir="${ETHOS_SECRETS_REPORT_DIR:-build/evidence/quality/secrets}"
mkdir -p "${report_dir}"

scan_parent="$(mktemp -d "${TMPDIR:-/tmp}/ethos-gitleaks-tracked.XXXXXX")"
scan_root="${scan_parent}/ethos-gitleaks-tracked"
mkdir -p "${scan_root}"
trap 'rm -rf "${scan_parent}"' EXIT

# Secret scanning is a source-quality gate over tracked files, not a host-state
# audit over ignored caches or generated local evidence. Materialize the Git
# tracked file set into an isolated mirror and scan that mirror as a regular
# directory so untracked `.cache/`, `build/`, and `.ethos/state/` residue cannot
# create false quality failures while tracked secrets still fail deterministically.
"${UV_PROJECT_ENVIRONMENT}/bin/python" - "${repo_root}" "${scan_root}" <<'PY'
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1])
scan_root = Path(sys.argv[2])
completed = subprocess.run(
    ["git", "ls-files", "-z"],
    cwd=repo,
    check=True,
    stdout=subprocess.PIPE,
)
for raw_path in completed.stdout.split(b"\0"):
    if not raw_path:
        continue
    relative = raw_path.decode("utf-8", errors="surrogateescape")
    source = repo / relative
    target = scan_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        os.symlink(os.readlink(source), target)
    elif source.is_file():
        shutil.copy2(source, target)
PY

# `--no-git` intentionally applies to the tracked-file mirror, not to the full
# worktree. `--redact` keeps matched values out of logs and the report.
gitleaks detect \
  --source "${scan_root}" \
  --config "${repo_root}/.gitleaks.toml" \
  --no-git \
  --redact \
  --report-format json \
  --report-path "${report_dir}/report.json"

# History scan is a separate hard gate: current tracked-tree cleanliness does not
# prove governed release history is free of leaked material. This scan traverses
# Git history, not ignored host-state residue.
gitleaks git \
  --config "${repo_root}/.gitleaks.toml" \
  --redact \
  --report-format json \
  --report-path "${report_dir}/history-report.json" \
  "${repo_root}"
