# Proposal

## Why

The six root commands run from the operation catalog (`2026-11-08-catalog-root`,
`2026-11-08-catalog-operations`), but 38 leaves still declare their own Cyclopts parameters and hold
their own bodies in `src/ethos/surface/cli/`: 26 under `lane`, 7 under `hook`, 3 under `attestation`
and `host run`. Their flags are parsed twice (Cyclopts and the argv rows in
`src/ethos/contracts/admission.py`), their destructive argv are listed by hand (12 rows), `next`
cannot name the operation they run, and 52 `ignore_imports` rows keep the surface importing the
adapters. Every group leaf should be one catalog entry that one generic adapter renders, so that
selection, help, exits and `next` come from one declaration.

## What Changes

- Every `lane`, `hook`, `attestation` and `host run` leaf becomes a catalog entry under a stable
  `<group> <leaf>` command and `<group>.<operation>[.<mode>]` ID. The kernel half sits in
  `ethos.contracts.operations`, one module per semantic group; the application half in
  `ethos.application`, mapped by `IMPLEMENTATIONS` per command with an operation override.
- One generic adapter builds each group's Cyclopts commands from the catalog and renders results;
  the per-leaf modules under `src/ethos/surface/cli/lane/`, `hook/` and `root/` retire, and
  `ethos mcp` stays a hand-written transport launcher.
- A `modes()` helper declares preview and apply pairs, reusable `Annotated` field types describe the
  recurring flags, and a `process` exit kind lets `host run` exit with its child's status.
- `next` classifies every ETHOS argv through the catalog; the 12 destructive argv rows and the group
  argv tables retire. A golden table of the old classifications gates the migration.
- **Breaking.** A group leaf that ignored an inapplicable flag now exits 2 with
  `command_field_refused`, and a usage error reports the full command path
  (`command_usage_invalid:lane start`). Positionals gain a keyword spelling (`lane start --name x`).
- The 52 group `ignore_imports` rows leave `.config/checks/import-linter/import-linter.toml`.
- The control-replacement fence follows the moved code, slice by slice.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: group commands derive from the operation catalog, the structured next step
  classifies every ETHOS argv through it, and the Cyclopts and CLI-delegation requirements name the
  one generic adapter for every command.

## Impact

- `src/ethos/contracts/operations/` (new group modules, `declaration.py`, `catalog.py`),
  `src/ethos/contracts/admission.py`, `src/ethos/contracts/next_step.py`.
- `src/ethos/application/` (`catalog.py`, new `lane/`, `hook/`, `attestation.py`, `host.py`,
  `docs_registry.py`; `peer_identity.py`, `redaction.py` and `retention.py` gain entries).
- `src/ethos/surface/cli/`: new `catalog.py`; `application.py`, `output.py`; the `lane/`, `hook/`
  and `root/{attestation,host,reference}.py` modules retire.
- `.config/checks/import-linter/import-linter.toml`,
  `src/ethos/adapters/admission/control/replacement.py`, `system/gates.toml`,
  `rules/module-layout.md`, `docs/reference/command-plane.md`, `CHANGELOG.md`.
- Tests: the catalog table test, a golden `next` data file under `tests/fixtures/`, a
  `(argv, command, exit)` table, help and refusal tests; the seven test files that import a group
  module are retargeted, rerouted or deleted. Adopters see no change for valid requests.
- Budget: at most +200 product and at most -100 test effective lines over the Change.
