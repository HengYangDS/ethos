#!/usr/bin/env bash
# Capture or verify that the current Git HEAD stayed stable for one evidence run.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  tools/ci/scripts/require-stable-head.sh capture
  tools/ci/scripts/require-stable-head.sh verify <expected-head> [label]
EOF
}

current_head() {
  git rev-parse HEAD
}

if (($# < 1)); then
  usage
  exit 64
fi

command="$1"
shift
case "${command}" in
  capture)
    if (($# != 0)); then
      usage
      exit 64
    fi
    current_head
    ;;
  verify)
    if (($# < 1 || $# > 2)); then
      usage
      exit 64
    fi
    expected_head="$1"
    label="${2:-evidence run}"
    observed_head="$(current_head)"
    if [[ "${observed_head}" != "${expected_head}" ]]; then
      {
        printf 'ETHOS head-stability guard failed for %s.\n' "${label}"
        printf 'expected_head=%s\n' "${expected_head}"
        printf 'observed_head=%s\n' "${observed_head}"
        printf 'discard this evidence and rerun on a stable head\n'
      } >&2
      exit 65
    fi
    ;;
  *)
    usage
    exit 64
    ;;
esac
