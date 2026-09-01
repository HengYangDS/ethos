## Context

See [proposal.md](proposal.md). An archive effect identifies the archived
Change and its original post-image. An authorized Work Lane refresh then emits
a ref Attestation whose nested Git-rebase effect binds the pre-refresh lane
head, candidate base, and rewritten output head. The archive reader currently
accepts only the original archive post-image as an ancestor, so a valid refresh
can make that authority undiscoverable.

## Goals / Non-Goals

**Goals:**

- Recover one exact archive authority through an attested refresh chain.
- Keep proof scope bound to the archived Change that owns the Work Lane work.
- Fail closed when the evidence chain is absent, ambiguous, or inconsistent.

**Non-Goals:**

- Adding persisted mappings, migration records, compatibility readers, or a
  second lifecycle.
- Inferring rewritten commits through patch identity or content similarity.
- Changing archive, refresh, or proof command syntax.

## Decisions

### Resolve identity from the existing Attestation graph

The archive-transition reader will first retain its direct-ancestor path. When
an archive effect's desired commit is no longer an ancestor, it will inspect
authorized refresh evidence and accept a rewritten tip only when one exact
chain binds the prior lane head to the current refreshed history. The nested
Git-rebase effect is the Git-coordinate authority; the enclosing refresh
Attestation establishes that the rewrite was the sanctioned lane operation.

This uses existing immutable evidence rather than introducing a mutable
archive-to-refresh index. A repository scan is acceptable here because archive
resolution is bounded by one Change and exact object identities.

### Validate semantics after following the rewrite

Resolving a rewritten Git tip is necessary but not sufficient. The reader will
verify that the rewritten tree still contains the expected official archive
post-image and that its Change identity matches the archive effect. A nearer
archive for another Change is never a fallback candidate.

This preserves semantic identity rather than treating ancestry or proximity as
authority.

### Return no authority on uncertainty

Missing links, multiple valid rewritten tips, malformed Attestations, or a
post-image mismatch yield no recovered archive transition. Existing callers
then expose a bounded gap instead of silently selecting unrelated intent.

## Risks / Trade-offs

- **Attestation traversal could admit an unrelated rebase.** Exact pre-image,
  output-head, lane-ref, and archive identity checks constrain every link.
- **Several successive refreshes may form a chain.** Traverse only validated
  links and reject forks or ambiguity; do not guess which branch is current.
- **Legacy evidence may lack the required bindings.** Fail closed. This change
  deliberately adds no compatibility state or heuristic recovery.
