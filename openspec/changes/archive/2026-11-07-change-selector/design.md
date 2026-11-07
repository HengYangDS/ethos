# Design

## Context

`requested_change(explicit)` in `src/ethos/adapters/openspec/selection.py` returns an explicit
Change or else `ETHOS_CHANGE`. Its readers sit at several depths: the current resolution, the
official governance report, Commitment compilation, proof admission and the relocation scope.
`plan` and `prove` pass their `--change` into the resolution and the proof query, while the status
observation, the merge report and the Git hooks that a landing starts read only the environment.

## Goals / Non-Goals

Goals:

- One explicit Change per invocation that every in-process reader and every child process sees.
- The same option on the CLI and the same input on MCP, taken from the operation's own signature.

Non-Goals:

- Retiring `ETHOS_CHANGE`. It stays the fallback for one window, as the operation-catalog design's
  compatibility decision states.
- Typed continuation inputs and the catalog's selector flags; later catalog Changes own them.

## Decisions

1. **Bind, then restore.** `selected_change(change)` sets `ETHOS_CHANGE` to the explicit value for
   the duration of the operation and restores the inherited value, or its absence, on exit,
   including on an exception. A context variable would not reach the hooks a landing starts, and
   threading a parameter through every reader would leave those children out as well.
2. **The operation owns the input.** `inspect_repository`, `plan_repository` and `land_repository`
   bind their `change`, so the MCP tools built from their signatures expose it. The `prove` and
   `lane prewrite` commands, which have no MCP tool, bind at the command.
3. **Absent selection preserves inference; invalid selection fails closed.** `None` leaves the
   environment untouched, and an empty or unknown value reaches the readers that already refuse
   it.
4. **Remedies name both inputs.** A selection that does not own the requested paths now asks the
   agent to drop `--change` or unset `ETHOS_CHANGE`, since unsetting the variable alone does not
   help when the option rebinds it.

## Risks / Trade-offs

- The binding changes process state. The MCP server drains each call before the next under one
  lock, so no other call observes a foreign selection; a test checks that the input is restored
  after a call.
- A gate child of `prove --change` now sees the Change, as it already does under
  `ETHOS_CHANGE=<id> ethos prove`; the test suite clears the variable for every test.
