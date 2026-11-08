# Proposal

## Why

The six root commands (`status`, `plan`, `adopt`, `prove`, `land`, `publish`) each parse their own
flags, select a mode by first match in their operation, and refuse or ignore unexpected flags
differently per mode; the MCP tools call the same operations through other signatures, so the CLI
and MCP can disagree on a refusal, and `next` reads root argv with a third parser. The operation
catalog (archived `rc-plan`, Appendix A) gives each root mode one declared entry, and this Change
moves the root group onto it (A5), after `closeout-rebinding-fence` made the closeout preview read
only. Design: `decisions-draft-2.md` with its review settlement.

## What Changes

- One catalog: 29 root operations declared in `ethos.contracts.operations`, one module per command
  with its request model, flag spellings and operations (selector predicates, request fields,
  effects, authorization kind, exit kind); `ethos.application.catalog` maps each command to its
  application operation.
- One selection for every transport: the CLI adapter, the five MCP operations and `prove_repository`
  select through `select_operation`, so a refusal is the same result everywhere.
- Fields have one role per entry (selector, request or refused); a request whose selectors match no
  entry, or that sets a refused field, exits 2 with `command_operation_unmatched` or
  `command_field_refused`, as JSON under `--json`. **Breaking.**
- Union fields are keyword-only; Cyclopts' own parse errors become `command_usage_invalid` results
  (exit 2); a result that cannot be delivered exits 3 for every command. **Breaking (exit status).**
- `next` classifies root argv through the selected entry; `next.form` names it.
- `ethos --help --json` prints the root catalog within a declared help payload budget.
- The direct `ethos publish --apply` without `--receipt` is removed. **Breaking.**

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: transport-independent meaning, the application package, the public command plane
  (next steps and help), continuation from explicit facts, fail-closed exits, Cyclopts and CLI
  delegation, and exact-request admission.
- `adapters`: admission before product audit (bare `publish --apply` removed).

## Impact

- New `src/ethos/contracts/operations/` and `src/ethos/application/catalog.py`; the six root command
  modules in `src/ethos/surface/cli/root/` replaced by the generic adapter `catalog.py`;
  `src/ethos/cli.py`, `src/ethos/surface/cli/application.py` and `output.py`,
  `src/ethos/contracts/admission.py`, `src/ethos/contracts/next_step.py`, `src/ethos/result.py`; the
  land, adoption, publication and proof operations lose the checks that only refused requests no
  operation takes. One implementation per operation and the root import edges follow in A5b.
- Tests: one catalog table test, a subprocess journey for usage and help output, a CLI, SDK and MCP
  parity test, the form check on every in-process run's `next`, and conversions of tests that assert
  retired codes or exits.
- Size: about +450 to +650 product, +220 to +320 test effective lines (draft 2, Decision 12).
