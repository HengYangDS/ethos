## Context

The typed repository profile deliberately rejects `.` as a repository root.
DDWG's old complete envelope used that value to represent its one root-level
normative document, `guidelines.md`; DDWG's candidate already replaces it with
the current `normative_sources` declaration. Accepted-root closeout validates
the old root before it can promote that candidate, so the strict parser blocks
the migration it was meant to protect.

## Goals / Non-Goals

**Goals:**

- Admit only the known complete former envelope plus its one documented
  root-level normative-source workaround.
- Produce the current typed representation deterministically before strict
  validation.
- Keep malformed and current-profile uses of `roots.rules = "."` rejected.

**Non-Goals:**

- Add a second profile schema, an adopter-specific command, or a generic
  repository-root alias.
- Alter DDWG's candidate content, bypass its proof/closeout gates, or mutate
  its accepted root directly.

## Decisions

### Normalize before the existing strict model

The loader already owns the bounded legacy-envelope bridge. Extend that one
normalizer only after all retired fields and their values exactly match the
former contract. If that exact payload contains `roots.rules = "."`, remove
only that invalid root entry so the typed default remains `rules`, then supply
`normative_sources = ["guidelines.md"]` only when the legacy declaration did
not already provide a source.

### Do not weaken current declarations

Current declarations never carry the retired envelope. They therefore continue
through strict Pydantic validation where `.` is invalid. The test matrix covers
the complete positive legacy form, preservation of an explicit source, and the
current invalid form.

### Keep the bridge local to profile interpretation

No DDWG files are changed by this implementation. After the product change is
proven and promoted, DDWG closeout will evaluate the old declaration through
this read-time bridge and still audit/prove the candidate's canonical tree.

## Risks / Trade-offs

- **A bridge becomes permissive compatibility debt** -> require the complete
  historical envelope, retain `extra="forbid"`, and add negative tests.
- **An inferred source overwrites declared truth** -> set the conventional
  source only when the legacy payload omits `normative_sources`.
- **A parser change is mistaken for DDWG promotion** -> keep product proof and
  DDWG closeout as separate HEAD-bound transitions.

## Migration Plan

1. Complete, test, and prove this one product change in its owned Work Lane.
2. Land it through ETHOS candidate and accepted-root closeout without remote
   publication claims.
3. Re-run DDWG's read-only closeout readiness against the exact candidate head.
4. Promote DDWG only through its governed closeout and then refresh the runner
   Work Lane; do not patch protected roots or session state.
