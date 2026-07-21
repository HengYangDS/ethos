#!/usr/bin/env bash
# Configure the runner's git checkout to match the repository's own commit policy so
# CI is a faithful ETHOS working copy. The dogfood signature-policy gate (ethos
# report / audit / quality commits) asserts the committing identity and signing setup
# match .ethos/workspace.toml [commit_policy]; a fresh CI checkout has neither, so
# read the policy from that single source of truth rather than hardcoding it here.
#
# Signing uses an ephemeral SSH key generated per run: the gate checks that signing
# is configured (gpgsign/format/key present), not that any specific key is trusted,
# so a throwaway key makes CI a faithful signing checkout without secret management.
#
# Kept outside .gitlab-ci.yml so CI stays a projection over reusable setup logic.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

IFS=$'\t' read -r name email signing_required signing_format <<EOF
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

def _str(key: str) -> str:
    value = policy.get(key)
    return value if isinstance(value, str) else ""

def _configured_identity() -> tuple[str, str]:
    expected_name = _str("expected_name")
    expected_email = _str("expected_email")
    if expected_name or expected_email:
        return expected_name, expected_email
    identities = policy.get("allowed_identities")
    if isinstance(identities, list):
        role_order = {"maintainer": 0, "team": 1, "bot": 2, "service": 3}
        candidates = [identity for identity in identities if isinstance(identity, dict)]
        candidates.sort(key=lambda identity: role_order.get(str(identity.get("role", "")), 99))
        for identity in candidates:
            name = identity.get("name")
            email = identity.get("email")
            if isinstance(name, str) and isinstance(email, str) and name and email:
                return name, email
    return "", ""

required = "1" if policy.get("signing_required") is True else ""
name, email = _configured_identity()
print(f"{name}\t{email}\t{required}\t{_str('signing_format')}")
PY
)
EOF

if [ -n "${name}" ]; then
  git config --local user.name "${name}"
fi
if [ -n "${email}" ]; then
  git config --local user.email "${email}"
fi
echo "git identity: $(git config --local --get user.name) <$(git config --local --get user.email)>"

if [ -n "${signing_required}" ]; then
  format="${signing_format:-ssh}"
  git config --local commit.gpgsign true
  git config --local gpg.format "${format}"
  # The CI checkout must not borrow a host-global (or a prior job's stale local)
  # signing key. Test execution deliberately hides global Git configuration, so
  # the checkout must own a current job-local key to remain self-consistent.
  if [ "${format}" = "ssh" ]; then
    key_dir="${TMPDIR:-/tmp}/ethos-ci-signing"
    mkdir -p "${key_dir}"
    key_path="${key_dir}/id_ed25519"
    if [ ! -f "${key_path}" ]; then
      ssh-keygen -t ed25519 -f "${key_path}" -N "" -C "ethos-ci@${CI_PROJECT_PATH:-local}" -q
    fi
    git config --local user.signingkey "${key_path}.pub"
  fi
  echo "commit signing: gpgsign=$(git config --local --get commit.gpgsign) format=$(git config --local --get gpg.format)"
fi
