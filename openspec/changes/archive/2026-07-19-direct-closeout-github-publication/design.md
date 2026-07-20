## Context

Campaign status currently aggregates two different questions into one required
publication-gap list: whether the publication contract itself is structurally
valid, and whether the long-running compression program has reached its final
state. The pre-push hook passes that list to the protected-push reducer, so
unmet terminal budget, active debt, active campaign state, and unretired steps
block an otherwise proven and locally closed `dev`/`main` update. The same hook
also omits its `--remote` value when calling the reducer, producing an `origin`
diagnostic for a GitHub push.

GitLab is presently unavailable by an explicit user boundary. GitHub is the
selected single remote plane until GitLab availability is re-observed; this is
not a statement that the two forge planes are synchronized.

## Goals / Non-Goals

**Goals:**

- Separate publication-contract blockers from campaign-progress advisories in a
  declarative, typed report.
- Keep structural campaign declaration errors fail-closed for protected push.
- Keep source-budget and debt truth visible for full proof and terminal
  compression closeout without making it a per-Change or ordinary GitHub push
  blocker.
- Preserve hook enforcement and make remote identity exact in diagnostics.

**Non-Goals:**

- Altering candidate-first accepted closeout, proof, identity, fast-forward, or
  branch-admission rules.
- Declaring GitLab healthy, altering GitLab, or treating local proof as hosted
  CI proof.
- Retiring remote refs or foreign Work Lanes.

## Decisions

1. **Split policy output into `required_gaps` and `advisory_gaps`.**
   The existing `publication` CEL rules continue to express structural defects:
   a source-budget campaign id that names no campaign remains a hard gap. A new
   declarative advisory rule group expresses active campaign state, unfinished
   steps, terminal budget progress, active debt, and source-budget progress.
   This lets the report remain complete without calling end-state progress a
   correctness defect for an ordinary protected update.

2. **Admission consumes only report required gaps.**
   `push_admission_report` will retain the report envelope but no longer turn
   campaign progress into `campaign_gaps`. Thus its existing branch policy,
   proof, topology, identity, reconciliation, and remote enforcement remain the
   sole blockers after base admission.

3. **Remote name is carried through both hook evaluations.**
   The initial and campaign-enriched calls to `push_admission_report` receive
   `remote_name=remote`. This makes topology lookup and emitted diagnostics
   match the remote Git actually invokes.

4. **Schema and docs describe the separation.**
   The workflow declaration and closeout schema add explicit advisory fields.
   Repository-governance and quality requirements retain terminal compression
   rigor while defining ordinary direct publication as local-closeout plus
   independent remote admission.

## Risks / Trade-offs

- **A campaign remains visibly incomplete after publication** → advisory fields
  stay explicit in the report, and full proof/terminal closeout retain their
  source-budget gates.
- **A malformed campaign could be hidden as advice** → declaration/bound
  campaign errors remain `required_gaps` and continue to block push.
- **A remote-plane assumption could be mistaken for synchronization** → docs and
  report semantics keep GitHub observation distinct from GitLab and hosted CI.

## Migration Plan

1. Add OpenSpec deltas, typed policy fields, and schema fields.
2. Change the report and hook/reducer behavior with regression tests.
3. Run focused policy, hook, schema, and OpenSpec validation before broader
   proof.
4. Land through the existing candidate-first local closeout. Then re-observe
   GitHub and perform an ordinary non-force `dev`/`main` push; rollback is a
   normal new locally closed commit, never a remote force update.

## Open Questions

None. GitLab restoration remains a later external-state observation.
