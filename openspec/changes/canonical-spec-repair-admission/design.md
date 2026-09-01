## Context

See `proposal.md`. During official Change bootstrap, ETHOS can observe both an
active Change and strict validation failures in already-archived canonical
specs. Even when the Change artifacts are complete and a Commitment has been
compiled, the current resolver returns the validation block before applying
normal material scope. Consequently the exact canonical file named by OpenSpec
cannot be repaired.

## Goals / Non-Goals

**Goals:**

- Derive a repair scope solely from fresh official validation gaps.
- Admit only exact canonical spec paths whose capability identifiers are valid.
- Compose the repair scope with active-Change attribution without persisting a
  second authority carrier.
- Preserve every existing Work Lane, Lease, runtime, editor-root, and path
  admission check.

**Non-Goals:**

- Admit arbitrary canonical-spec edits.
- Treat warnings or stale diagnostics as reusable authority.
- Allow source, tests, docs, configuration, or unrelated Change artifacts
  through the repair path.
- Change Commitment or Lease schemas.

## Decisions

### Derive repair paths from the current official report

The OpenSpec lifecycle adapter will translate only gaps of the exact form
`openspec_validation_failed:spec:<capability>` into
`openspec/specs/<capability>/spec.md`. Capability identifiers pass the same
logical identifier validation used elsewhere. The derived set is ephemeral and
comes from the same current report that blocks normal compilation.

Alternative rejected: infer repairs from filesystem contents or validator text.
That would broaden authority beyond the machine-readable official result.

### Compose a narrow recovery scope before ordinary bootstrap fallback

When requested paths are a subset of the derived repair set, the resolver
returns an attributed repair scope owned by the single selected active Change.
Mixed requests remain blocked path-by-path. Once official validation passes,
the repair scope disappears automatically and normal Commitment material scope
is the only path.

Alternative rejected: ignore validation gaps while compiling a Commitment.
That would weaken the acceptance contract and allow implementation to proceed
against invalid canonical specifications.

### Keep the repair authority stateless

No repair token, file, database row, compatibility switch, or special command
is introduced. Prewrite re-observes official OpenSpec and derives the exact
scope on every request.

Alternative rejected: a break-glass flag. It would make bypass authorization a
user-controlled assertion rather than a fact-derived decision.

## Risks / Trade-offs

- **A validator emits a malformed capability id** -> identifier validation
  yields no repair authority and prewrite remains fail-closed.
- **A request mixes one valid repair with another path** -> the unmatched path
  is reported as uncovered and the whole mutation remains blocked.
- **Validation changes between prewrite and edit** -> normal mutation hooks and
  subsequent prewrite re-observation prevent reusable authorization claims.

## Migration Plan

Add regression tests first, implement the narrow derived scope, run focused and
full proof, land and install a source-independent accepted runtime, then rerun
the originally blocked adopter prewrite. No stored state migration is needed.
