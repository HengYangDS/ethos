# Proposal

## Why

The archived `rc-plan` design places this row in Family 3 (lines 89-95): `store-retention` follows
the application package and precedes `residue-class` and `proof-output-scratch`. Its decision 5,
items 1 and 2 (lines 199-205), and Appendix D.5 (lines 735-739) add three things to the landed
retention verb: the verb is a catalog entry whose destructive apply follows the catalog's
authorization rule, byte budgets cover its stores and are observed for 48 hours before the release
candidate, and the explicit, previewed release of an absent consumer joins it. The committee's
resolution of 2026-11-14 places the row in 0.2.0-beta.13, and the release-candidate gate lists all
three under its item on retention (`docs/decisions/dr-0026-release-candidate-gate.md`).

At the base the first is held and the other two are not:

- The verb is an entry of `ethos.application` and its apply is declared destructive and
  authorized (`src/ethos/application/catalog.py`, `src/ethos/contracts/operations/hook.py`).
- `retention.status_bytes` is declared in the paradigm and no code reads it
  (`grep -rn status_bytes src tests docs` prints two lines, both in `paradigm.toml`). No command
  reports a store's bytes, and the host store has no budget row. On the releasing checkout the
  directories that the retirement verb owns held 3,680,372 KiB on 2026-11-17 (`du -sk`,
  allocated blocks: artifacts 1,054,208; lane retirement requests 1,516,148, receipts 1,105,260,
  manifests 3,312 and operations 1,444), against the declared 1 GiB; the whole store held
  12,405,092 KiB.
- A consumer whose path is gone keeps its installations and is named in a report, and no command
  releases it. The changelog lists that among the known open defects of 0.2.0-beta.11
  (`CHANGELOG.md`). On the host where this Change was prepared the host store's `installations`
  held five runtime copies of 687,372 to 695,212 KiB each (`du -d 2 -k` over the host data root's
  `ethos` directory).

## What Changes

- `ethos hook retire-supply --release-absent` previews the consumer records whose repository path
  the host reports as absent, with the installations each one holds and their bytes. Only
  `--expect-plan <digest> --apply --authorize` releases them. The release unlinks records and
  removes no installation: the cleanup that ends `hook install` retires an installation that no
  record needs.
- The release reads absence itself. Only the host's answer that no entry exists counts; a place it
  cannot look at is unknown and is never planned, alike on every supported interpreter.
- A repository at a scanned root that names an installation is recorded as its consumer before a
  record is released, so a moved repository keeps what it selects.
- The preview of `ethos hook retire-records` reports the files and bytes under each top-level name
  of the store, the time of the read, and one budget row: the bytes of the owned kinds against
  `retention.status_bytes`, as `within` or `over`.
- The paradigm gains `retention.host_bytes`, the budget of the host store's installations, and the
  preview of `hook retire-supply` reports that row.
- A budget only reports. No verdict, exit or required gap changes, and no command refuses for
  bytes.

Not breaking: without the new switch `hook retire-supply` plans and applies what it did, and both
previews only gain fields.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a new requirement, `An absent consumer is released only by a previewed step`.
- `repository-governance`: a new requirement, `Store byte budgets report and never refuse`.

## Impact

- `src/ethos/adapters/repo/runtime/materialization/host_retention.py`,
  `src/ethos/application/hook/installation.py` and `src/ethos/contracts/operations/hook.py` for
  the release; a new module `src/ethos/adapters/store/retention/budget.py` and
  `src/ethos/application/retention.py` for the report;
  `src/ethos/contracts/paradigm/paradigm.toml` for the new row.
- The command reference, the local-state page and the changelog, whose known defect this closes.
- Size, measured by the budget tool on each patch: 124.1 product and 289.8 test line-equivalents
  for the release, 66.9 and 128.0 for the report and the two rows.
- Not here: the 48-hour observation itself, which is a task of the release owner; `ethos status`
  naming a budget row that is over; the three record kinds that the archived apply design left to
  `record-retirement-kinds`; authorization by delegation, which its own row owns.
