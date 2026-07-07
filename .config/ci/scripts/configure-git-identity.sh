#!/usr/bin/env bash
# Configure git identity from the repository's own commit policy so the CI runner
# checkout is a faithful ETHOS working copy. The dogfood signature-policy gate
# (ethos report / audit) asserts the committing identity matches the configured
# expected author in .ethos/workspace.toml [commit_policy]; a fresh CI checkout has
# no identity, so read it from that single source of truth rather than hardcoding.
#
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

IFS=$'\t' read -r name email <<EOF
$(python3 - <<'PY'
import tomllib
from pathlib import Path

policy: dict[str, object] = {}
path = Path(".ethos/workspace.toml")
if path.exists():
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    raw = data.get("commit_policy")
    if isinstance(raw, dict):
        policy = raw
name = policy.get("expected_name") if isinstance(policy.get("expected_name"), str) else ""
email = policy.get("expected_email") if isinstance(policy.get("expected_email"), str) else ""
print(f"{name}\t{email}")
PY
)
EOF

if [ -n "${name}" ]; then
  git config user.name "${name}"
fi
if [ -n "${email}" ]; then
  git config user.email "${email}"
fi
echo "git identity: $(git config --get user.name) <$(git config --get user.email)>"
