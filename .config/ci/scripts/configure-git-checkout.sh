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


required = "1" if policy.get("signing_required") is True else ""
print(f"{_str('expected_name')}\t{_str('expected_email')}\t{required}\t{_str('signing_format')}")
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

if [ -n "${signing_required}" ]; then
  format="${signing_format:-ssh}"
  git config commit.gpgsign true
  git config gpg.format "${format}"
  if [ "${format}" = "ssh" ] && [ -z "$(git config --get user.signingkey || true)" ]; then
    key_dir="${TMPDIR:-/tmp}/ethos-ci-signing"
    mkdir -p "${key_dir}"
    key_path="${key_dir}/id_ed25519"
    if [ ! -f "${key_path}" ]; then
      ssh-keygen -t ed25519 -f "${key_path}" -N "" -C "ethos-ci@${CI_PROJECT_PATH:-local}" -q
    fi
    git config user.signingkey "${key_path}.pub"
  fi
  echo "commit signing: gpgsign=$(git config --get commit.gpgsign) format=$(git config --get gpg.format)"
fi
