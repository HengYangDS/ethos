#!/usr/bin/env bash
# Run the secret-scanning gate. Secret policy lives in the root .gitleaks.toml
# (gitleaks requires the config at a git-discoverable location); the concern is
# registered under .config/checks/secrets/.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${script_dir}/install-gitleaks.sh"

report_dir="${ETHOS_SECRETS_REPORT_DIR:-build/evidence/quality/secrets}"
mkdir -p "${report_dir}"

# Full working-tree scan (`--no-git`) so the gate fails on any secret currently
# present in tracked files, independent of commit history. `--redact` keeps the
# matched value out of logs and the report.
gitleaks detect \
  --source . \
  --config .gitleaks.toml \
  --no-git \
  --redact \
  --report-format json \
  --report-path "${report_dir}/report.json"
