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

The terminal seal is meaningful only when its producing gates run in the
checkout's declared semantic environment. The type gate therefore passes the
checkout-local `build/runtime/venv` to `ty`; it must not discover a host or
root `.venv` incidentally. The Python lint, Ruff-ratchet, and Bandit owner
scripts use Bash 3.2-compatible path collection, preserving the same tracked
file semantics without requiring a newer shell.

## Alternatives

- Ignore root caches in the topology gate: rejected because it weakens the
  repository-root boundary.
- Clean from `generated-artifacts`: rejected because a read-only audit must not
  hide producer defects or alter standalone behavior.
- Add a retry: rejected because retry masks a non-closed proof sequence.
- Fall back to host site-packages or root `.venv` for types: rejected because
  a Work Lane would no longer prove against its own semantic runtime.
- Require a newer Bash: rejected because a workstation package choice must not
  become a repository verification prerequisite.

## Proof Strategy

- Red-test that the default graph orders the topology seal after Ruff and the
  Python test gate.
- Red-test that test-gate EXIT cleanup invokes the denied-residue cleanup.
- Red-test that `ty` receives the semantic runtime path and that affected
  owner scripts contain no Bash-4-only `mapfile` dependency.
- Run focused tests, owner lint/config/shell gates, strict OpenSpec validation,
  changed-scope plan, and a HEAD-bound executed product proof.
