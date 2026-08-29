---
name: ethos-change-lifecycle
description: Use when driving an ETHOS change through the public status, plan, prove, land, and publish commands.
---

# ETHOS Change Lifecycle

## When to Use

Use this skill for the public lifecycle loop
`status -> plan -> prove -> land -> publish`. ETHOS
governs whether a change may land or publish from evidence, not assertion.

## Workflow

1. Run `ethos status --json`; confirm the checkout role and read `required_gaps`.
   Never mutate an accepted root directly.
2. Run `ethos plan --changed --json` to compile the plan for the changed paths,
   required gates, and required evidence.
3. Run `ethos prove --json` for a dry-run check; run
   `ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json` for an
   executed proof. Only `--execute` produces HEAD-bound evidence.
4. Run `ethos land --json`; the verdict gates the fast-forward to the candidate
   role. A blocked verdict refuses (non-zero exit); read `required_gaps`.
5. Run `ethos publish --json` for local publication readiness. Select one
   positively admitted full ref with `ethos publish --ref <full-ref>
   --probe-remote --expect-head <head> --json`. Add `--apply --authorize` to
   consume that request in the same operation, or apply the receipt explicitly
   for restartable execution. Branches and annotated release tags use the same
   exact-object CAS executor and recheck every declared peer before any push.
   In proposal/MR mode, select `refs/heads/proposal/<slug>` from the proved
   candidate object; candidate and Work Lane refs themselves remain local-only.

## Evidence

Use the public `ethos` command plane; its JSON is machine evidence:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
ethos land --json
ethos publish --ref <full-ref> --probe-remote --expect-head "$(git rev-parse HEAD)" --json
ethos status --json
```

Evidence boundaries (enforced in `system/evidence_boundaries.toml`): dry-run
readiness != executed proof; digest-bound != semantic correctness; local != hosted;
promotion != absolute correctness (only: a bounded claim was admitted).

## Convergence Discipline

- Count progress only when an acceptance gap closes; file churn and reruns are
  not progress.
- Freeze the complete candidate before expensive checks, run the smallest
  discriminating test first, then affected-domain tests, and reserve the full
  proof for the atomic-task boundary.
- A tool yield is not a test timeout. Resume the same live process instead of
  duplicating it.

### Learn While Delivering

- Normalize each failure to a stable signature before fixing it. A renamed
  symbol with several stale callers is one migration-closure failure, not many
  unrelated import errors.
- First occurrence: fix the root cause and add the smallest discriminating
  regression. Second occurrence: stop local patching and remove the competing
  owner or execution path. Third occurrence: the atomic task remains incomplete
  until the lesson is encoded in the existing rule or skill and an executable
  gate, test, schema, or scaffold makes recurrence observable or unreachable.
- After a destructive move or rename, immediately prove the reference closure:
  search the whole repository for the retired surface, then run focused import
  collection and type analysis before adding more behavior. Do not postpone
  closure to the final full suite.
- At each atomic commit boundary record, in the existing authoritative task or
  skill rather than a parallel diary: the acceptance gap closed, the duplicate
  path deleted, the normalized failure signature, and the mechanism that now
  prevents or detects recurrence.
- Review and full-suite reruns do not count as learning. Learning is complete
  only when future execution changes because the repository now carries the
  lesson.

## Bundled Resources

- `scripts/readiness.py` — deterministic read-only driver: runs status -> plan ->
  prove (readiness) in order, parses each verdict, prints the first blocking gap with
  its next action. Read-only; never lands, publishes, or executes proof. Run it
  before a land to see the whole readiness picture in one pass.
- `references/verdicts-and-gaps.md` — how to read the loop's JSON verdicts and act on
  common `required_gaps` (a skill-specific lookup not in the repository). Read it when
  a gap is unfamiliar.

## Trust Boundary

This skill is a workflow package projection. Repository truth — source, tests,
schemas, official OpenSpec records, Attestations, and fresh ETHOS observations —
remains above any skill text. Commitment is compiled transiently.
