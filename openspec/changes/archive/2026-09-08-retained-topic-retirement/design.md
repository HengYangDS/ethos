## Context

Two historical clean topics share nine commits; one has a tenth commit. Git
ancestry proves that removing the shorter topic loses no commit while the longer
ref survives. It does not prove that their semantics are accepted. Current
`superseded` combines authoring-successor authority with resource retention and
cannot express this deletion-only transition.

## Decisions

- Keep one linked-retirement owner. A full `refs/heads/...` value supplied through
  `--absorbed-by` selects the surviving local ref explicitly; an arbitrary OID
  alone does not prove durable retention.
- Require an accepted control checkout, explicit actor and reason, a clean topic
  target, exact target HEAD, known target Lease, and ownership for a valid Lease.
  Neither target nor retained ref may be a protected or candidate role; the
  retained ref must differ from the deleted ref and contain the deleted HEAD.
- Retention is fresh Git evidence, not authority to write the surviving checkout.
  Bind its ref/OID alongside accepted-ref assertions in the existing transaction.
  Recheck before worktree removal and let Git verify the assertion atomically
  with target deletion. Unknown, moved, missing, or unrelated retention blocks.
- Derivation persists the existing immutable retirement operation and returns
  `lane retire recover` with its receipt path and digest. Direct full-ref apply
  is rejected; it cannot silently resolve a newer retained OID than the one
  reviewed. No additional continuation contract or storage is introduced.
- Compile no product Commitment for this deletion-only transition. Reuse existing
  immutable retirement operation, actor checks, Lease lock, Git effect, partial
  recovery, and terminal receipt. Do not add a persisted retention registry.
- Reference-transaction uses accepted policy only for an exact admitted retirement
  intent, including historical targets that cannot supply current policy. It
  never infers deletion permission merely from an unrecognized branch name.
- Honor the user-directed budget correction at the existing quality owner, not
  in retirement admission. Keep required product/test ceilings and permit omitted
  optional ceilings to mean observation-only, never zero or infinity. The native
  declaration sets product and tests to 40000; no project-total limit is declared.
  Existing explicitly declared optional limits still enforce their own boundaries.
  Generated Mermaid output uses the existing generated-evidence accounting class;
  its handwritten C4 input and generator remain source. Archive accounting and
  Python ELOC measurement are unchanged. This is a bounded execution-constraint
  correction, not a broader metrics redesign or a reason to defer retirement.

## Preservation And Exit

The surviving ref and checkout remain unchanged. The receipt says retained
history, not accepted absorption. Unique semantic work stays attached to that
surviving root and must still be adjudicated before its final retirement.

The focused regression uses two real divergent topic histories and installed
hooks, exercises dry-run and apply, and checks target absence plus unchanged
accepted and retained objects. Negative cases cover dirty, foreign Lease,
wrong/missing/self retention, protected roles, stale source, and retained-ref
movement between plan and effect. Existing retirement recovery tests remain.
