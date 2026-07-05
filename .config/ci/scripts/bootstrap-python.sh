#!/usr/bin/env bash
# Shared GitLab Python bootstrap. CI YAML is a provider projection; this script is
# the local SSOT for Python/uv/OpenSpec setup used by hosted jobs.
set -euo pipefail

python -m pip install --upgrade pip >/dev/null
pip install uv
printf '%s\n' '#!/usr/bin/env bash' 'exec npx --yes @fission-ai/openspec "$@"' > /usr/local/bin/openspec
chmod +x /usr/local/bin/openspec
uv --version
