## Context

The accepted checkout owns the installed Git hook and the ref transaction it
protects. The candidate checkout owns the new control logic and proof-bound tree
under evaluation. These duties are intentionally different: retaining the hook
shell in accepted preserves the boundary, while invoking accepted-old Python to
judge a candidate control change makes the verdict stale by construction.

## Goals / Non-Goals

**Goals:**

- Evaluate an accepted prepared transaction with source and runner resolved
  from the clean candidate checkout whose HEAD equals `new_value`.
- Preserve fail-closed behavior and all existing closeout predicates.
- Keep ordinary non-accepted ref admission on the local checkout runtime path.

**Non-Goals:**

- The candidate does not install or replace the accepted hook shell.
- The candidate does not self-authorize promotion, bypass independent control
  replacement, weaken proof, or permit raw ref movement.
- No profile-specific or compatibility admission path is added.

## Decisions

1. **Accepted shell, candidate reducer.** Resolve the configured candidate
   worktree from Git metadata; require configured branch, exact HEAD, clean
   source state, checkout-local runner, and source roots physically below that
   candidate root. Invoke its reducer with `--root <accepted-root>`. This keeps
   semantic policy current while the protected ref boundary remains accepted.

2. **No accepted-old fallback.** Candidate binding failure rejects the accepted
   transition. Falling back would make policy selection depend on incumbent
   code, exactly the condition being removed.

3. **Retain explicit local runtime for other refs.** The candidate binding is
   narrowly for accepted prepared transitions. Work-lane and other ref events
   continue through their checkout-bound runtime so lease repair and ordinary
   admission retain their existing provenance.

4. **Prove behavior by skew.** The regression makes accepted-old hook code fail
   and candidate code remain valid; sanctioned closeout must pass, while a raw
   move remains blocked. This tests provenance rather than merely happy-path
   output.

## Risks / Trade-offs

- **Candidate worktree absent or stale** → fail closed with an actionable hook
  diagnostic; no fallback is allowed.
- **Candidate local runtime is untracked** → permitted only when ignored; any
  tracked or ordinary untracked source delta blocks reproducibility.
- **Canonical contract collision during integration** → replay this lane from
  current candidate and preserve both independently scoped requirements before
  proof; do not overwrite foreign integration content.

## Migration Plan

1. Start a fresh lane at the current candidate head and declare this change.
2. Add the candidate-runner contract, hook implementation, and skew regression.
3. Run focused admission tests, static shell/runtime contracts, lint, claim
   validation, and strict OpenSpec validation; then archive the completed Change.
4. Refresh and commit generic parity evidence on the archived lane tree, then
   execute HEAD-bound proof before candidate landing. Re-prove the resulting
   candidate before separate accepted closeout and retirement.
