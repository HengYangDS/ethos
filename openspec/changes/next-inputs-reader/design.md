# Design

## Context

See the [proposal](proposal.md). `EthosResult.next` is a computed field: `derive_next_step`
(`src/ethos/contracts/next_step.py`) builds it from `next_action`, the continuation and the first
gap. `EthosResult.from_payload` (`src/ethos/result.py`) validates a carried `next` only for its
shape and derives its own. `NextStep` refuses an unknown member, and the tracked result schema says
the same, so both refuse a result that carries `inputs`.

The readers that parse `next`:

- in the product, `EthosResult.from_payload` and the result schema
  (`system/schemas/kernel/result.schema.json`), which a test holds equal to the model's schema;
- in the tools, `tools/ci/delivery/acceptance/invocation.py`: `invoke` reads every result through
  `from_payload`, and `continuation` reads the step's kind and argv; the installed-package check in
  `effect.py` calls the installed build's `from_payload`;
- in the tests' support, the check in `tests/support/ethos_cli_runner.py` that every step of an
  in-process run parses as a live command.

The product's readers of another process's result (gate verification, the predecessor policy probe,
hook admission and rollback) expand the result and read its verdict, gaps and data, never `next`.
They need no change, and the hook path gains no import.

Two product functions copy a result into a new one from a dump: `with_runtime`
(`src/ethos/application/result_projection.py`) and `apply_payload_budget`. Every result that a
surface prints passes through both.

The operation catalog (`src/ethos/contracts/operations/`) describes a request field by three things:
its name, its flag (`Command.flag`) and its help text (`described`). `ethos <command> --help --json`
prints them as `flags` and `request_schema`.

## Goals / Non-Goals

Goals:

- A build one release older than the first producer parses a result that carries `inputs`, keeps
  them and exposes them unchanged.
- A step without a value to choose keeps the bytes it has today.
- The order is visible in the build: no producer names the inputs.

Non-Goals:

- Any producer, `--actor`, or the typed steps of `environment-entry` and N1.
- Which kinds of step may carry inputs, and how a reader binds a chosen value into an argv or an
  MCP call. The producers' Change and the golden-path journey own both.
- The Skills and the quickstart. They are matched to a version, so they name `inputs` with the
  release that emits it.
- The `delegation` authority. The schema has admitted its authorization kind since the catalog.

## Decisions

1. **An input is a name, a flag and a description.** These are the catalog's own three words for a
   request field, so an input is no second vocabulary. `name` is the field that the value fills,
   which a binding and `--help --json` name alike; `flag` is its command-line spelling;
   `description` is its help text. All three are required strings. An input has no type and no
   default: the request schema of the operation that `next.form` names owns them. The committee
   draft's richer entry (a JSON Schema, a default and a reason) is not taken.
2. **The entry is closed.** `NextInput` is strict and frozen and refuses an unknown member, as
   `NextStep` does. An open entry would let a later member pass a reader that cannot act on it, and
   every model of the result contract is closed.
3. **Absent when empty.** `NextStep.inputs` defaults to empty and is left out of the wire then, so
   no result, fixture or golden file changes. The schema lists the member as optional.
4. **A reader keeps the carried inputs, and only them.** No text renders an input, so a reader
   cannot derive it. `from_payload` validates the carried step, derives the kind, form, argv,
   effects, destructiveness, authorization, binding and reason itself, and takes `inputs` from the
   carried step. They name values and grant nothing.
5. **The model holds them beside the step.** `EthosResult.next_inputs` is a field that serialization
   leaves out, and the computed `next` carries it. The wire has one carrier, `next.inputs`: a
   top-level `next_inputs` in a payload is never read. Refusing it would need a new refusal name for
   a key that no build writes.
6. **One owner copies a result.** `EthosResult.replace` rebuilds a result from every field, also one
   that a dump leaves out, and validates it as a new result. `with_runtime` and
   `apply_payload_budget` use it, so no copy drops the inputs and neither names them.
7. **A source scan pins the order.** Only `contracts/next_step.py` and `result.py` may name
   `NextInput` or `next_inputs`; a producer has to name one of them. The scan lives in its own test
   module, which the first producer's Change deletes whole. A check in the tests' CLI support was
   not taken: that support must itself read a result with inputs.
8. **The reference states the reader rule only.** One sentence of the result envelope changes and no
   line is added: the document holds 499 of its 500 nonblank lines. Its list of members gains
   `inputs` with the release that emits it, as its authorization list leaves out `delegation`.
9. **One requirement is added and one is modified.** The new requirement owns the member and the
   order of reader and producer. `The structured next step derives from the exact rendered argv`
   changes because its readers no longer check a carried step for shape alone. The requirement
   `Public Command Plane` lists what a step names and stays true, and the kernel's `never trusted`
   still holds for everything that grants authority.

## Risks / Trade-offs

- A closed entry means that a member the producers find missing needs its own reader release first.
  The three members cover the actor, a Change name, paths and a reason, which are the values that
  the plan names.
- A reader keeps a value that it cannot check. A forged `flag` such as `--apply` would have an agent
  complete the argv into another operation than `next.form` names. The inputs grant nothing, and
  the command that runs the completed argv selects and authorizes its operation again. The
  producers' Change should refuse an input whose flag selects an operation.
- A reader does not compare `name` with its own catalog, since an older reader may not know a newer
  field, and it accepts inputs on any kind of step, also on `done`.
- The scan cannot see a producer that writes a raw payload without the result model. No product
  module does.
- `replace` validates the copy again, as both copies did before.
