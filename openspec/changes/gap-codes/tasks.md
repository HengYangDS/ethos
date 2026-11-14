# Tasks

## 1. The registry

- [ ] 1.1 Add `src/ethos/contracts/codes/gaps.toml`, one sorted row per code plus the `[family]`
      prefixes. Done when `tomllib` reads it, every code of the census of 2026-11-14 is a row or a
      family member, and the three small tables' codes are rows or prefixes.
- [ ] 1.2 Add the standard-library loader `gaps.py` beside it. Done when `gap_code`, `registered`,
      `record` and `repair_for` pass their cases and an unregistered code reports None, not a raise.
- [ ] 1.3 Add the two-way static test `tests/architecture/test_gap_registry.py`. Done when a planted
      unregistered literal at a refusal position fails it, a planted absent row fails it, and the
      tree as landed passes.
- [ ] 1.4 Add the runner guard in `tests/support/ethos_cli_runner.py`. Done when an unregistered
      code in a result's `required_gaps` fails with the code named, and the focused suites that use
      the runner pass.

## 2. The exit table

- [ ] 2.1 Declare `ExitRow` and `EXIT_CODES` in `contracts/operations/declaration.py`, with
      `refused` 125 reserved and no exit number changed. Done when each row's case passes and no
      numeric `SystemExit` argument remains under `src/ethos/surface/`.
- [ ] 2.2 Exit by kind in `output.py` and publish the table as `data.exits` in help. Done when
      `ethos --help --json` prints all six rows and the root help stays within its payload budget.

## 3. Texts

- [ ] 3.1 Add the CHANGELOG line and the `docs/reference/command-plane.md` sentence; add the two
      ADDED requirements to `kernel` and `command-plane`. Done when `openspec validate gap-codes
--strict` passes and the Markdown check is clean.

## 4. Lane and hosted

- [ ] 4.1 Regenerate the rows on the lane head after the three Changes beside this one land. Done
      when the static test passes at the lane head and every new or moved code has its row.
- [ ] 4.2 Pass readiness and the precheck on the committed lane head. Done when each passes with no
      finding.
- [ ] 4.3 Land, tag beta.11 and publish. Done when the tag exists on both peers and the release
      record names this Change.
