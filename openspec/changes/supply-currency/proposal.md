# Proposal

## Why

ETHOS ships the latest stable supply that its constraints allow. Read on 2026-10-31 against the
official registries and release feeds, 24 of its 86 supply pins were behind, and the native
resolvers then found more: `uv lock --upgrade` updates 24 locked Python packages and drops 8 that no
locked package requires any more, npm reports ESLint 10.14.0 and OpenSpec 1.16.0, and Mise reports
Node 26.13.0, the first LTS release of Node 26. Python stays within `>=3.12,<3.15`.

## What Changes

- Python: `uv lock --upgrade` moves `uv.lock` and the quality sample's lock to the latest admitted
  releases, among them uv 0.13.6, Ruff 0.17.3, ty 0.0.95, pytest 9.2.0, pydantic 2.14.2 and
  hatchling 1.33.0. Each direct floor in `pyproject.toml` rises to its locked version, as the
  dependency declaration check requires.
- npm: ESLint 10.14.0, OpenSpec 1.16.0 and the re2js override 2.9.1.
- Mise: Node 26.13.0, CPython 3.14.10 from python-build-standalone 20261026, and the floor
  2026.10.24 with the six official executable digests that CI bootstraps.
- CI: setup-uv 10.3.3 selecting uv 0.13.6, and mise-action 5.2.4 in the shipped adopter CI model,
  each pinned by commit.
- Supply image: the base `uv:0.13.6-python3.14-trixie-slim` by index digest, and ca-certificates
  `20250419+deb13u1` from trixie-security.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a supply refresh under the existing quality and runtime contracts, so
`skip_specs: true` applies.

## Impact

- The installed runtime ships CPython 3.14.10, Node 26.13.0, OpenSpec 1.16.0, uv 0.13.6 and Ruff
  0.17.3. OpenSpec 1.16.0 fails `validate --strict`, which ETHOS runs, on a scenario without a WHEN
  or GIVEN step or without a THEN step.
- GitLab's supply manifest check refuses the landed head until the supply image is rebuilt from it
  and bound. The binding is its own Change, and GitLab receives the head only with it.
