#!/usr/bin/env bash
# Download one CI tool artifact with bounded retries, resumable partial files, and
# an atomic destination. This helper is intentionally small: install scripts own
# tool-specific URL, archive validation, and extraction; this helper only owns the
# transport policy shared by hosted CI and local fallback gates.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: .config/ci/scripts/download-file.sh <url> <destination>" >&2
  exit 2
fi

url="$1"
destination="$2"
attempts="${ETHOS_CI_DOWNLOAD_ATTEMPTS:-4}"
delay_seconds="${ETHOS_CI_DOWNLOAD_RETRY_DELAY_SECONDS:-3}"
connect_timeout_seconds="${ETHOS_CI_DOWNLOAD_CONNECT_TIMEOUT_SECONDS:-20}"
max_time_seconds="${ETHOS_CI_DOWNLOAD_MAX_TIME_SECONDS:-600}"
low_speed_limit="${ETHOS_CI_DOWNLOAD_LOW_SPEED_LIMIT:-1024}"
low_speed_time_seconds="${ETHOS_CI_DOWNLOAD_LOW_SPEED_TIME_SECONDS:-30}"

require_positive_integer() {
  local name="$1"
  local value="$2"
  case "${value}" in
    ''|*[!0-9]*)
      echo "${name} must be a positive integer" >&2
      exit 2
      ;;
  esac
  if [ "${value}" -lt 1 ]; then
    echo "${name} must be at least 1" >&2
    exit 2
  fi
}

require_positive_integer ETHOS_CI_DOWNLOAD_ATTEMPTS "${attempts}"
require_positive_integer ETHOS_CI_DOWNLOAD_RETRY_DELAY_SECONDS "${delay_seconds}"
require_positive_integer ETHOS_CI_DOWNLOAD_CONNECT_TIMEOUT_SECONDS "${connect_timeout_seconds}"
require_positive_integer ETHOS_CI_DOWNLOAD_MAX_TIME_SECONDS "${max_time_seconds}"
require_positive_integer ETHOS_CI_DOWNLOAD_LOW_SPEED_LIMIT "${low_speed_limit}"
require_positive_integer ETHOS_CI_DOWNLOAD_LOW_SPEED_TIME_SECONDS "${low_speed_time_seconds}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for CI artifact download" >&2
  exit 127
fi

case "${destination}" in
  */*) mkdir -p "${destination%/*}" ;;
esac

partial="${destination}.part"
trap 'rm -f "${partial}.tmp"' EXIT HUP INT TERM

download_once() {
  if [ -s "${partial}" ]; then
    echo "Resuming partial CI artifact download: ${url}" >&2
    if curl --fail --location --show-error \
      --continue-at - \
      --connect-timeout "${connect_timeout_seconds}" \
      --max-time "${max_time_seconds}" \
      --speed-limit "${low_speed_limit}" \
      --speed-time "${low_speed_time_seconds}" \
      --output "${partial}" \
      "${url}"; then
      return 0
    fi
    local status="$?"
    if [ "${status}" -eq 33 ]; then
      echo "Server rejected resume; restarting CI artifact download: ${url}" >&2
      rm -f "${partial}"
    else
      return "${status}"
    fi
  fi

  curl --fail --location --show-error \
    --connect-timeout "${connect_timeout_seconds}" \
    --max-time "${max_time_seconds}" \
    --speed-limit "${low_speed_limit}" \
    --speed-time "${low_speed_time_seconds}" \
    --output "${partial}" \
    "${url}"
}

attempt=1
while :; do
  if download_once && [ -s "${partial}" ]; then
    mv "${partial}" "${destination}"
    exit 0
  fi
  status="$?"
  if [ "${attempt}" -ge "${attempts}" ]; then
    echo "CI artifact download failed after ${attempts} attempt(s): ${url}" >&2
    exit "${status}"
  fi
  echo "CI artifact download failed with status ${status}; retrying ${attempt}/${attempts}: ${url}" >&2
  sleep "${delay_seconds}"
  attempt=$((attempt + 1))
done
