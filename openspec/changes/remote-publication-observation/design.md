## Context

The exact-object publication path already has one `PublicationEffect`, one
content-addressed request, exact force-with-lease execution, post-observation,
and terminal Attestation. Its target observer calls `ls-remote` once per target
ref without a timeout. Unavailable observations are then coerced through an
empty string into push admission, where accepted-branch ancestry checks
manufacture `accepted_ref_move_not_fast_forward`.

## Goals / Non-Goals

**Goals:**

- one bounded remote-ref observation for each exact publication target;
- a lossless distinction between `present`, `absent`, and `unavailable`;
- `unknown` for unavailable required facts and `block` only for observed failed
  conditions;
- complete diagnostic coordinates without another receipt or state machine;
- no network process surviving the bounded observation.

**Non-Goals:**

- remote retry policy, backoff, background workers, or periodic polling;
- peer publication ordering or hosted-CI parity waiting;
- a new remote schema, compatibility reader, provider wrapper, or error
  registry;
- changes to AIGW or Proxy.

## Decisions

### 1. Observe once at the effect boundary

The exact-ref observer remains the sole live target observer for exact
publication and is owned by `mutation/publication/observation.py` beside the
publication Attestation owner. Readiness-only publication may continue using
its separate advisory availability projection because it neither compiles nor
authorizes a remote effect.

Alternative rejected: infer exact target state from remote-tracking refs or a
general reachability probe. Neither observes the selected full ref.

### 2. Preserve three semantic outcomes

`present` carries the exact object coordinates. `absent` carries the repository
zero OID. `unavailable` carries no OID and includes the failed command boundary.
The publication compiler does not call push admission, ancestry checks, or
`PublicationUpdate` construction for an unavailable target.

Alternative rejected: represent unavailable as empty or zero OID. Empty is not
a Git fact, and zero means the ref was positively observed absent.

### 3. Derive the public verdict from fact availability

An unavailable required remote observation yields public verdict `unknown` and
names only the missing remote fact. An observed divergent OID remains `block`.
Both cases fail closed, but they are different continuations and must not share
a fabricated ancestry gap.

### 4. Reuse the existing receipt and executor

No request receipt is created until all target observations are complete and
the plan passes. Apply re-observes the same targets through the same bounded
observer. Existing exact-CAS, partial-effect evidence, and terminal Attestation
remain unchanged.

## Risks / Trade-offs

- A short timeout may classify a slow peer as unknown. This is truthful and
  safely retryable; it must not be converted into a history verdict.
- Removing the duplicate availability probe changes diagnostic shape. Focused
  tests must prove one exact target observation owns the mutation decision.
- Timeout exceptions contain implementation-shaped text. The observation also
  records explicit argv and cwd so consumers do not depend on that text.

## Migration Plan

1. Add failing focused tests for timeout and unavailable observation.
2. Bound and enrich the existing exact-ref observer.
3. Stop admission/ancestry compilation for unavailable targets and project
   `unknown` from the same observation.
4. Delete the duplicate exact-publication availability call and stale tests.
5. Run focused publication, Git-adapter, result-algebra, and reference-closure
   checks before exact-HEAD proof and lifecycle closeout.

Exact-HEAD proof, official archive, candidate/accepted CAS, runtime activation,
remote publication, and Work Lane retirement are governance effects evidenced
after tracked implementation tasks are complete. They are not tracked as active
Change tasks because doing so would make official archive depend on effects that
can only occur after archive.
