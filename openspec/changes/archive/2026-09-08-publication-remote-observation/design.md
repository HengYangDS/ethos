## Context

See `proposal.md`. The remote publication effect adapter already owns source
validation and exact peer/ref observation. It can lawfully return an effect
gap before any peer observation exists. The CLI consumer currently assumes
that every configured peer/ref has an observation whenever projection mode is
active and indexes a coordinate that was never observed.

## Goals / Non-Goals

**Goals:**

- Treat only complete `present` and `absent` observations as inputs to push
  admission.
- Preserve effect-adapter gaps unchanged when observation did not occur.
- Prove the public command returns structured JSON for a pre-observation source
  failure.

**Non-Goals:**

- No SSH-specific branch, ref shorthand compatibility, new observer, retry, or
  provider projection.
- No change to source trust, exact-CAS, fast-forward, or publication authority.
- No repair of the separate build-identity interaction with untracked files.

## Decisions

### Filter at the observation consumer

The CLI admission fold will derive reports only from observations whose state
is `present` or `absent` and whose `object_oid` is a non-empty string. Missing,
unavailable, or malformed observations produce no local push-admission report;
the effect adapter's existing gaps remain the sole explanation.

Alternative rejected: synthesize an unavailable observation in every early
return from the effect adapter. Source validation occurs before remote work and
there is no peer fact to attach; manufacturing one would misstate epistemic
state and duplicate target construction.

### Regress the public command

The regression uses a repository with a valid publication topology and proof
but an untrusted publication source. The adapter therefore returns a source
gap and no observations. The test asserts structured `block`, the exact source
gap, empty push admission, and no remote mutation.

Alternative rejected: test only the private helper. That would not prove the
CLI envelope or protect against a later orchestration regression.

## Risks / Trade-offs

- **Risk: malformed successful observations are silently ignored.** → Require
  both an admitted state and non-empty OID; their native owner remains the
  observation contract, while the CLI never invents a diagnosis.
- **Risk: a missing report hides a proof gap.** → Effect and proof gaps are
  folded independently before reports; this change removes only invalid report
  construction.

## Migration Plan

1. Add and observe the public failing regression.
2. Restrict report derivation to complete observations.
3. Run focused publication tests and strict OpenSpec validation.
4. Complete exact-HEAD proof, archive, local acceptance, immutable runtime
   installation, and a read-only Workstation probe.
