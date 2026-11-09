# Proposal

## Why

The docs registry accepts an adopter's retained history and evidence originals once the native
observer verifies each one's bytes and mode against the declared taxonomy, but the shared paradigm
still judges them as authored documents. `governance_audit` passes the retained-origin observation
to the docs and semantic-closure reports and not to `repository_paradigm_report`, so its
front-matter, decision-record, authored-name and formatter checks refuse every original, and
`ethos lane repair-paradigm` could plan a front-matter edit that rewrites one. Codex 019f4fbf
reproduced the contradiction on an adopter with 122 declared originals.

## What Changes

- The docs registry exposes the paths it verifies as retained originals, or none when the
  observation has a gap, differs from the declaration or is missing.
- The paradigm report takes the observation and removes those paths from the inputs of its
  front-matter, decision-record, authored-name and formatter checks, and from nothing else.
- `ethos lane repair-paradigm` observes the originals once and passes the observation to both of
  its reports, so it plans no edit of a verified original.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: a verified retained original is not an authored document.

## Impact

- `src/ethos/repository/registry/docs/registry.py`, `src/ethos/repository/paradigm/report.py`,
  `src/ethos/repository/audit.py` and `src/ethos/adapters/mutation/paradigm_repair.py`.
- Paradigm report and repair tests.
- No path allowlist, no second registry, no adopter workaround and no rewrite of historical bytes;
  a repository without declared originals is unaffected.
