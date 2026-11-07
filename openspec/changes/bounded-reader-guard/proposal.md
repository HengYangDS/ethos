# Proposal

## Why

Since result schema 3 bounded every large JSON result, four readers have read a bounded result as if
it were complete (register row 29):

- the hosted verification receipt;
- landing's predecessor policy probe, which blocked every self-hosted landing;
- the candidate reference-transaction reader;
- the rollback preflight.

The requirement `Readers of another ETHOS process read its result in full` exists, but nothing
ties a new reader to `expand_result`. Two readers still miss the bound today:
`tools/ci/delivery/acceptance/mcp.py` parses the installed CLI's stdout directly, and
`adapters/gates/verification.py` reads the gaps of an ETHOS-shaped gate result without expanding
it.

## What Changes

- An architecture test finds each reader of an ETHOS result and requires it to expand a bounded
  result. A reader is found in one of two ways: a JSON parse of stdout in a module whose argv runs
  ETHOS, or any JSON parse whose result is read for ETHOS's own fields or shape.
- The MCP acceptance reads the CLI's result through `invocation.invoke`, the one reader path of
  delivery acceptance.
- Gate verification expands a bounded ETHOS-shaped result before it reads the verdict and gaps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The test enforces an existing requirement, so `skip_specs: true` applies.

## Impact

- `tests/architecture/test_bounded_result_readers.py`, `tools/ci/delivery/acceptance/mcp.py` and
  `src/ethos/adapters/gates/verification.py`.
