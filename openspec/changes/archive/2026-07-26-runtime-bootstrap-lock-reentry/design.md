## Context

`with-python-runtime.sh` is the repository-owned boundary between a checkout's
semantic Python environment and `uv`.  Its semantic-Python path currently
recognizes a projectless runtime and otherwise asks `uv` to verify or create the
runtime.  The full proof runner already marks its owner path with
`ETHOS_RUNTIME_BOOTSTRAPPED=1` and uses `--no-sync` to avoid re-entering the
same runtime lock.

A real armed reference-transaction closeout exercises a remaining path: while
that outer proof owns the lock, the hook requests the current checkout's exact
semantic Python.  The bootstrap treats it as an ordinary request, re-enters
`uv`, and can wait indefinitely on the outer process.  No ref is advanced, but
the required proof never produces a receipt.

## Goals / Non-Goals

**Goals:**

- Make a marked request for the exact healthy semantic Python execute directly.
- Preserve missing-runtime bootstrap, unmarked requests, explicit interpreter
overrides, and fail-closed accepted-ref admission.
- Prove the fix without relying on timing or a long-running deadlock test.

**Non-Goals:**

- Do not change reference-transaction policy, candidate routing, leases, or
closeout authorization.
- Do not broaden the marker into a general bypass for arbitrary commands or
interpreters.
- Do not change cache topology, add a lock manager, or touch foreign Work
Lanes, remote publication, or host state.

## Decisions

### 1. Narrow the direct-execution path to the existing bootstrap protocol

Inside the branch that already proves the requested executable equals the
current worktree's `build/runtime/venv/bin/python`, first accept only all of:

- `ETHOS_RUNTIME_BOOTSTRAPPED=1`;
- an executable semantic Python; and
- that semantic runtime's `pyvenv.cfg`.

When all predicates hold, the bootstrap directly executes the original argv.
It does not run `uv sync --check` or a nested `uv run`.  The existing unmarked,
missing, and invalid-runtime paths remain unchanged.

A broader `ETHOS_RUNTIME_BOOTSTRAPPED` bypass was rejected because it could
skip runtime binding for an arbitrary command.  Checking only the marker and
Python path was rejected because a stale or forged runtime lacks the normal
`pyvenv.cfg` health boundary.

### 2. Bind to the current computed semantic path, not an inherited root

The wrapper resets `UV_PROJECT_ENVIRONMENT` to the current worktree before it
dispatches.  The exact semantic path therefore binds the direct execution to
that checkout.  It must not require an inherited `ETHOS_RUNTIME_ROOT` to equal
the current root: a hook can legitimately inherit an outer runtime root while
being dispatched in a different checkout.

### 3. Use a deterministic wrapper regression

The regression creates a valid semantic interpreter and `pyvenv.cfg` in a
project-bearing scratch repository, sets the marker, and supplies a fake `uv`
that records any invocation.  Success requires the semantic interpreter's
output and no `uv` record.  The pre-existing tests retain coverage for the
projectless direct path, failed sync fallback, and owner-script `--no-sync`
handoff.

## Risks / Trade-offs

- [A stale marker reaches an arbitrary command] → The guard remains inside the
  exact semantic-Python branch and requires executable plus `pyvenv.cfg`.
- [A cross-worktree hook inherits a different runtime root] → The condition
  deliberately relies on the recomputed current semantic path, not the
  inherited root.
- [A future edit moves the guard after `uv`] → The focused fake-`uv` regression
  fails on any attempted synchronization.

## Migration Plan

1. Add the specification, Claim, and Chronicle carrier.
2. Add the failing deterministic regression, then the narrow shell guard.
3. Run focused runtime and armed-hook tests, strict OpenSpec validation,
   parity refresh, and an exact-HEAD executed proof.
4. Archive the carrier only after its implementation checklist is complete.
   Candidate land, accepted-root closeout, lane retirement, and publication
   remain separate governed transitions.

## Open Questions

None.
