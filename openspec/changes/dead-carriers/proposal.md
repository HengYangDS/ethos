# Proposal

## Why

Design move 8 ("no dead carriers", route phase 1) deletes carriers that no decision reads. At
`18ed740e0` two kinds remain that pass every check and keep a loader, schema or session alive:

- `system/formats.toml` (43 lines), `system/routing.toml` (11) and `system/evidence-boundaries.toml`
  (90) are read only for their presence and their schema: `system_contracts_report` validates them,
  and nothing reads a value inside them. The three TOML files do not ship, their schemas ship under
  `ethos/resources/system/schemas/contracts/` without an installed reader, and no governed repository
  refers to them. `system/surfaces.toml` stays, because the semantic closure reads its identities.
- The repository gate `svg-format` runs the Nox session `svg_lint`, which calls
  `source_format_report` on `*.svg`, the same provider that the shipped `source-format` gate runs
  over every authored file. Its row, its session and the `svg-assets` validation command restate one
  property.

## What Changes

- Delete the three system contracts and their schemas under `system/schemas/contracts/`;
  `SYSTEM_CONTRACTS` keeps `surfaces`.
- Delete the `svg-format` gate from `system/repository-gates.toml` and the `svg_lint` session; the
  `svg-assets` ownership row names the shipped `source-format` gate as its validation command.
- Point the documents and the format policy row that name a deleted contract at their current owner.

Out of scope, each for its own Change: the gate fields `network_policy` and `version_source`, which
no decision reads but ten governed repositories set and `Gate` refuses unknown fields; the six
schemas that `repository/audit.py` only lists; the `shell-lint` gate, which the product-shell
paradigm rule retires with the shell ownership row; and the repository registry's `skills` row,
which attributes the provider's source to ETHOS's own tree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This deletes carriers that no requirement names, so `skip_specs: true` applies.

## Impact

`system/`, `src/ethos/contracts/system/contracts.py`, `tools/ci/sessions.py`,
`.config/checks/format-selection/policy.toml`, the tests that list the deleted carriers, and the
documents that link them. No lock, supply or adopter change.
