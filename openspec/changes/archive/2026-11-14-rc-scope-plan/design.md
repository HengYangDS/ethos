# Design

## Context

The release candidate of 0.2.0 is bound to a gate of thirteen items
(`docs/decisions/dr-0021-release-scope-0-2-0.md`), whose text DR-0026 now records. The order that
reaches it lives in three archived designs: `rc-plan` (eight families, with sizes and
prerequisites), `product-form-plan` (the first hour, the agent budgets, the adopter bump) and
`common-base-plan` (thirteen Changes, three of them before the freeze). On 2026-11-13 they left 51
open rows.

A review classed each row by the gate's words: 42 are required or lower a measured cost, three
are waived by the owner, and six carry no gate text. Nine rows had landed in the seven days after
`rc-plan`, three of them after its first day, so the order below also changes how rows are
prepared. Fifteen kept rows have no size and fifteen have no converged design; each of those gets
its design before its batch.

## Goals / Non-Goals

Goals:

- One tracked order for the rows that the release candidate needs, by weekly batch.
- Breaking changes and the agent path in use for a week before the freeze.
- A measure of progress that a session other than the author's can read.

Non-Goals:

- Designing any row. Each opens as its own Change and cites this design for its batch.
- Changing a requirement. The waivers' effects on the specifications arrive with their own rows.
- The work after 0.2.0, except its first Change.

## Decisions

1. **The scope is 42 rows and four small ones.** The 42 are 39 that the gate requires and three
   that lower a measured cost: `ci-economy`, the routed first step of `status` (N1) and the
   first-hour document (N5). The waivers and the review add four small rows: the MCP preview guard;
   the surface texts with the golden path's amended acceptance; the amendment of the 900-second
   requirement, if the measured proof needs it; and the gate's tracked text, which is this Change.
   Two rows without gate text are kept: `record-roots-one-owner`, and one attempt at
   `brew-channel`. DR-0026 holds the three waivers and the rows that leave.
2. **Four weekly batches.** A row lands after the rows it names as prerequisites, and a reader
   ships one release before its producers.
   - **beta.11, 2026-11-21:** `ci-economy`; `github-pin`; `pin-selection`; `adopt-pin`;
     `release-identity`; `adopter-bump`; `ci-commit-trust`; the reader of `environment-entry`'s
     `inputs`; `gap-codes`; `provider-ids`; `hook-install-converge`; `host-reservation`; this
     Change. Breaking: none.
   - **beta.12, 2026-11-28:** `release-acceptance`; `hermetic-journey`; `release-predecessors`;
     `full-suite-legs`; `journey-hosts`; `store-retention`; `residue-class`;
     `proof-output-scratch`; `gate-environment`; the producers of `environment-entry`;
     `hosted-observation`; `fast-tier`; `record-roots-one-owner`. Breaking: continuations drop the
     actor export, and the release ref needs a passing hosted observation on each CI peer; each
     ships with the repair that its design names.
   - **beta.13, 2026-12-05, the first rehearsed release:** `release-rehearsal`;
     `rehearsal-admission`; `release-provenance`; `lane-operations`; `run-handles`; `gate-reuse`;
     `reference-workstation`; `http-retirement`; the public normal path (N4); N1; N5;
     `secret-scan-supply`; `evidence-ref-scan-scope`; `build-audit-offline`; the MCP preview guard;
     the surface texts. Breaking: the exit codes that `lane-operations` changes, and MCP effect
     tools that stay off unless enabled at launch. The eleven adopter pins are in before
     `http-retirement`.
   - **beta.14, 2026-12-12, frozen:** `rollback-after-repair`; `stable-release-path`;
     `release-time-budget`; the two diagnoses and the proof across the nightly boundary; the
     900-second amendment, if needed; the attempt at `brew-channel`; `golden-path-journey`.
     Breaking: none.

   The golden path's hosted journeys run once against beta.13's published bytes, as a dry run
   before their Change lands in beta.14.

3. **`fast-tier` leads beta.12.** It has no design yet, so it cannot lead beta.11. Until it lands,
   the lane's own check before each proof covers ETHOS's batches. Its design also takes two measured
   gaps: a focused run reads as blocked although every selected gate passed, and `status` shows no
   repository gap on a copy without hooks.
4. **Rows are prepared in parallel and landed in batches.** Each row is prepared as a patch against
   a named base in its own disposable clone, and the lane lands three to five per proof. A patch
   carries its base commit, a validated Change directory, its exact paths, the focused gate output
   on that base, three measured budget deltas, the shared files it edits with its order among them,
   and the repair for any breaking change. The CI model and the distribution owner are serial:
   `ci-economy` edits the CI model first.
5. **Three outcomes judge the release.**
   - An agent that is not the author walks the golden path on `next` alone. The agent path's nine
     rows deliver it. The journey's executor has no model, so two walks by another session's agent
     are recorded, on beta.13 and on the frozen beta.
   - The adopter that another person maintains upgrades. The pin chain, the bump and
     `release-predecessors` deliver it. Missing: repository gaps shown on a copy without hooks,
     which `fast-tier`'s design takes, and a stated path from a release outside the support window.
   - A count of the wrong changes that each release blocked and that escaped. No row delivers it;
     from beta.12 each release's notes carry a hand count, and the product does not count it in
     0.2.0.

   `host-reservation` is accepted only when a foreground host proof holds the host ticket and one
   read lists the queue and its holder. `run-handles` gives the ticket to detached runs only, so the
   two rows together remove the session-side load checks.

6. **Budgets are checked per batch.** By the plans' estimates the product ends near 82,600 of
   85,000 line-equivalents, the tests near 105,600 of 105,000 and the tools near 9,800 of 10,000.
   The tests reach DR-0023's revisit point during beta.11: that review runs then, densification
   first, and a standalone step lands in beta.12 if the measured need remains. DR-0025's review
   runs if the unsized rows take the product past 83,000. Every added tools line names a removal.
7. **Work outside the row count.** The eleven adopter pins after beta.11 and the eleven bumps to the
   frozen beta, in the adopters' own lanes; four release Changes with their release days; the test
   revisit; the 48-hour retention observation; the inventory of kit-created Keychain items before
   the kit retires; and, before each tag, the candidate's bump and proof on disposable copies of
   the governed repositories, which DR-0026 names as the substitute for the waived fixtures.
8. **Owner tasks on the public forge.** Before beta.13's tag: the protected release environment
   and immutable releases. At `ci-economy`'s landing: the ruleset that requires only its aggregate
   check, and the lockfile policy.
9. **After 0.2.0.** The second landing of the history rebuild, with its record-draft operation, is
   the first Change of the first weekly batch after the stable release. It is prepared as a patch
   during the soak, and its budget step is decided before the soak ends.
10. **The measure.** Each weekly batch reports the gate rows left, 42 on 2026-11-14, and the rows
    archived from the order. A session other than the author's reads the report.

## Risks / Trade-offs

- The dates need about two rows closed each working day, four times the measured rate. The signal
  by 2026-11-21: the three retention rows have sized designs, and `lane-operations`' patch passes
  its local journey without a model in a disposable clone. Without both, the freeze moves a week.
- One author. Parallel preparation moves the limit to review and to the one proof host.
- The golden path's Change lands in the frozen batch. Its dry run on beta.13 lowers the risk and
  does not remove it: a fault that only the frozen beta shows moves the candidate to 2026-12-26.
- No plan states whether the first tag that carries `release-rehearsal` can itself be rehearsed.
  If it cannot, the rule of the release time budget moves the freeze one week.
- The sizes are estimates, and one landed row measured above its estimate for both landings.
- The other maintainer may not upgrade; the second outcome then stays open at the release.
