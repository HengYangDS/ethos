# Design

## Context

The official quality specification makes root `.pytest_cache/` and
`.ruff_cache/` denied generated homes. `ethos quality generated-artifacts`
must remain a read-only standalone audit of that fact. The product proof,
however, is a sequence and must evaluate its topology verdict after the gates
that can produce or clean runtime state.

## Design

The product proof graph adds `generated-artifacts` dependencies on `ruff` and
`unit-architecture` only when those product-owned runtime gates are selected.
The shared registry remains profile-neutral so adopter graphs, which correctly
omit product Python gates, stay executable. This is a composition-time
sequencing constraint, not an exception in artifact policy: a cache remaining
at the root at the final seal still blocks proof.

`run-python-tests.sh` already clears denied root runtime residue before the
test run. Its EXIT cleanup will call the same cleanup function before releasing
the evidence lock, so success, failure, and interruption share one residue
postcondition.

## Alternatives

- Ignore root caches in the topology gate: rejected because it weakens the
  repository-root boundary.
- Clean from `generated-artifacts`: rejected because a read-only audit must not
  hide producer defects or alter standalone behavior.
- Add a retry: rejected because retry masks a non-closed proof sequence.

## Proof Strategy

- Red-test that the default graph orders the topology seal after Ruff and the
  Python test gate.
- Red-test that test-gate EXIT cleanup invokes the denied-residue cleanup.
- Run focused tests, owner lint/config/shell gates, strict OpenSpec validation,
  changed-scope plan, and a HEAD-bound executed product proof.
