---
subject: ethos:discoverability-ux-dx
state: proven
created: 2026-07-06
claim: discoverability-ux-dx
head: pending-before-commit
---

# Discoverability UX/DX Evidence

## Claim

ETHOS exposes a thin orientation reader view for humans and agents without
creating a parallel truth store. `ethos orient --json` derives role, capability,
coordination, readiness, and next actions from repository status and report
truth. `ethos status --json` keeps existing workspace-status fields pure; `ethos orient --json` provides the projection packet.

## Net gain

- Humans get a concise terminal first glance instead of a single opaque status
  line.
- Agents get a stable JSON orientation packet with explicit projection boundary,
  mutation prewrite hint, and foreign-lane observe-only hint.
- Foreign Work Lane visibility becomes safer: discoverable does not imply write,
  land, or retire authority.
- No new semantic center is created; orientation mints no truth and satisfies no
  proof.

## Checks

- Focused tests: `36 passed` across orientation, status contract, workspace-status schema, and validation gates.
- Full Python tests: `720 passed`, coverage `95.13%`.
- `run-python-lint.sh`: passed with ratchets preserved (`PLR0911 6/6`, `PLR0913 37/37`).
- `run-config-lint.sh`: passed.
- `run-shell-lint.sh`: passed.
- `ethos quality schemas --json`: `ok=true`, `state=clean`.
- `ethos quality claims --json`: `ok=true`, `state=clean`.
- `ethos openspec --lifecycle --json`: `ok=true`, `state=clean`.
- `ethos report --json`: `ok=true`, `score=16/16`, `governance_gap_count=0`, `parity_pending_count=0`.
- `ethos orient --json` was observed with `state=oriented`, `truth_boundary=repository-reader-view`, and `mints_truth=false`.
- `ethos status --json` preserves pure workspace-status fields and validates the emitted data against `workspace-status.schema.json`; `ethos orient --json` provides the separate orientation projection.

## Boundaries

This evidence does not claim remote CI, hosted UI behavior, or completion of all
future UX surfaces. It records repository-local CLI and JSON orientation checks
for the current change.
