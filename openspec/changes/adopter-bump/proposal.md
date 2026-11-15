# Proposal

## Why

No ETHOS operation moves a repository from one release to the next. `ethos adopt` writes a first
pin and refuses a Mise configuration that selects another release or holds the `http:ethos`
table, so every upgrade is hand work: the committee's reading of 2026-11-14 counts, for one
release, 79 files in seven lanes, 41 of them written by hand.

This Change is the adopter bump of the pin chain. The archived `common-base-plan` design
(decision 4) places it after `adopt-pin`, and the archived `product-form-plan` design
(decision 10) states its scope. DR-0029 moves it to the second batch, 0.2.0-beta.12, "in the
owner's full scope, with the handler for the older selector form", and makes "files written by
hand per bump" a weekly measure whose target is 0.

This Change does not bring that measure to 0. It removes the pin from the hand, and it names the
lock and the projection steps. The bump lane's Change record and its changelog line stay with the
hand until a later row gives them a writer.

## What Changes

- `ethos lane repair-paradigm` gains `--pin`. With it the repair plan first declares the bare
  entry of the release that runs the command as the repository's ETHOS selection in
  `.config/mise/config.toml`. An older bare pin and the `http:ethos` table both become that entry,
  and a tree without a selection gets its first pin, in the same admitted patch as the plan's
  other repairs.
- After an apply that wrote the selection, the next action is `mise --cd <root> lock`, and the
  result's ordered actions then name `ethos lane project --root <root> --json` where the
  repository declares projections. ETHOS runs neither.
- A tree that selects a newer release blocks the request with `runtime_pin_ahead:<version>` and
  plans nothing; its next action runs the same request with the release that the tree selects.
- A pin with options, a configuration that holds both forms and a development build are reported
  as `runtime-pin` and get no edit.
- `ethos adopt`'s conflict for a selection that this move replaces names
  `ethos lane repair-paradigm --pin --root <root> --json` and says that it runs in a Work Lane.
- Without `--pin` the command and the paradigm report do not change, and adoption's own pin step
  for a repository that is not yet adopted does not change.

Not breaking: the gap and the refusal exist only on request, and no audit, proof, landing or
publication reads them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: ADDED requirement
  `The paradigm repair declares the ETHOS selection on request`.

## Impact

`src/ethos/repository/paradigm/repair.py` and `toolchain.py`,
`src/ethos/adapters/mutation/paradigm_repair.py`, `src/ethos/adapters/repo/adoption.py`,
`src/ethos/application/adoption.py`, `src/ethos/application/lane/repair.py`,
`src/ethos/contracts/operations/lane_repair.py`, `src/ethos/contracts/codes/gaps.toml`,
`tests/unit/cli/test_lane_paradigm_repair.py`, `tests/unit/adoption/test_pin.py`,
`docs/architecture/adoption-profiles.md`, `docs/reference/operational-roots.md`, `CHANGELOG.md`
and the `repository-paradigm` spec through this Change's delta.
