---
subject: ethos:decision:release-candidate-gate
role: decision
state: canonical
decision_id: DR-0026
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/distribution/spec.md
---

# DR-0026: The 0.2.0 Release Candidate Gate Is Recorded With Three Waivers

Status: canonical rationale. The distribution specification owns current behavior.

Date: 2026-11-14.

Purpose: preserve what the release candidate of 0.2.0 requires, which three requirements the owner
waived and what stands in for each, which work leaves 0.2.0, and why the list was not cut further.

See also: [DR-0021: Release 0.2.0 declares three journeys and narrows DR-0015's
hosts](dr-0021-release-scope-0-2-0.md), [DR-0006: Proof trust
boundary](dr-0006-proof-trust-boundary.md), [DR-0024: History is rebuilt once, under one
Change-local record, with originals held locally](dr-0024-history-rebuild-map.md) and the `rc-plan`,
`product-form-plan`, `common-base-plan` and `rc-scope-plan` OpenSpec Changes.

## Context

DR-0021 binds the release candidate of 0.2.0 to the release-candidate items of the committee
resolution of 2026-11-07. That resolution was never tracked. The `rc-plan` design cites its items by
number, R1 to R13, and does not state them, so no tracked text said what the gate requires. The
resolution's scope rule is that an item blocks the release candidate until its acceptance holds or a
recorded owner decision waives it, and no place held such a record.

By 2026-11-13 the order held 51 open rows: the Changes of the `rc-plan` design that were not yet
archived, and the rows that the `product-form-plan` and `common-base-plan` designs added. Nine rows
had landed in the seven days after the plan, three of them after its first day. A review classed
each open row by the gate's own words. It found 42 rows required, three that lower a measured cost
and six without gate text. Two review seats rejected its first draft on three blocking findings: a
date range that was the best case, and two waivers costed by their savings only. A second draft
answered every finding, and the owner decided on it on 2026-11-14.

## Decision

- **The rule.** An item of the gate blocks the release candidate until its acceptance holds or a
  recorded owner decision waives it. A waiver names the words it waives, what 0.2.0 then lacks and
  what stands in for it. This record holds the first three. The items below state each
  requirement by shape; the designs of the order carry its acceptance in detail.
- **R1, the operation surface.** Every operation that takes a Change from its start to its
  retirement is public and described, and its result carries a bound next step without a template,
  prose or an environment step. That covers the lane operations, a detached proof with a handle, the
  actor as a typed binding, registered gap and exit codes, help for every parameter and usage errors
  as data. A remote write, a release or a destructive step stops at a typed result that names the
  approval it needs. Acceptance is a hosted golden-path journey on installed bytes, driven by an
  executor that runs only the returned next step, for a fixture repository and for a self-hosted
  root; one real lane run without operator scripts; and a detached proof that outlives its launcher.
- **R2, one application package.** One package owns every public operation and a catalog that names
  no transport, and every surface is a projection of it. Gate providers resolve by catalog identity,
  with earlier names mapped as data for one support window. A form that the candidate does not
  qualify is named so in its release entry.
- **R3, the size measure.** Done: DR-0019.
- **R4, the release path.** Before a tag, a declared step rehearses the release on hosted runners,
  from each release that an active adopter pins, and tag admission requires its receipt. The
  journeys cover DR-0021's hosts. A rollback after a repair is exercised. The full suite runs once
  per release on the other platforms and Python versions. The stable release has a complete,
  rehearsed path and a measured time budget.
- **R5, proof throughput.** The reference workstation is declared by hardware class, every proof
  reports time per gate, readiness gains a fast behavior tier, and a gate's result is reused only on
  byte-equal inputs with one coverage decision per attempt. The 900-second requirement is met or is
  amended with the measurements.
- **R6, the plan in its owners.** Each converged design is a proposal-stage Change, or a record
  defers it with an owner, a next action and a review date.
- **R7, retention.** A consumer whose path is gone is unknown, and only an explicit, previewed step
  releases it. Lanes stop holding gate evidence, and a landed lane retires with declared, natively
  checked residue. The stores have byte budgets and a 48-hour observation.
- **R8, security.** Remote effects over MCP need a confirmation that the server starts, and effect
  tools stay off unless the person who launches the server enables them. Release provenance names
  the tag, installation verifies it by source and signer, the checksum file is attested, releases
  are immutable and the release job runs in a protected environment. Proof gates run with an
  allow-listed environment, or the contract states the boundary. The secret scan resolves through
  locked supply and says when it is unarmed. The disposition of private-class addresses in
  ETHOS's own history is recorded, and the npm distribution is retired; both are done.
- **R9, the fleet.** Every adopter outside the deferred and archived ones pins the release it runs
  in the attested form. No adopter builds ETHOS from source. Activation never moves back to an older
  pin without a receipt. Releases batch weekly, and a support window in cadence time replaces a
  rebind per beta. One adopter's local checks stop reading ETHOS's evidence refs.
- **R10, the projections.** Skills, the quickstart and the hosted journey read the typed next step,
  and each host has one install line that names an attested channel.
- **R11, test quality.** Two recorded faults are diagnosed, one proof runs across the nightly
  boundary, and the build stops waiting on the networked vulnerability lookup.
- **R12, the shared host.** Guest processors fit inside the declared reservation, renders run
  through host admission, scratch carries an owner mark, and a tracked guest runbook holds no
  address and no token.
- **R13, ceremony.** Not a feature: the lean path stays inside the contract's limits, and a
  pin-only bump does not take it.
- **Waiver 1, the MCP projection.** MCP ships in 0.2.0 as a preview, the alternative that R2 names.
  Of R8, the annotations derived from the effect contract, the confirmation that the server
  starts and the real-client refusal test are waived. R8's rule that effect tools stay off is
  kept by a small row: the preview server registers no effect tool unless it is enabled at
  launch. Where a person enables them, authorization is still set by the caller. The golden path
  loses its MCP client leg.
- **Waiver 2, delegation authority.** R1's approval carrier, a repository-declared and scoped
  delegation, and the delegation legs of R1's acceptance are waived. 0.2.0 has no scope, expiry,
  revocation or approver key for an agent's remote writes. Authorization stays a flag that the
  caller sets, so an agent's remote write still passes on its own flag, and the entry documents
  and the release entry say so. The steps that stop for a person today still do. The rule that
  every remote write, release and destructive continuation awaits a person unless a delegation
  covers it moves to 0.3.0 with the delegation, and the authorization argument changes there,
  once, after a stable release.
- **Waiver 3, the journey fixtures.** R4's pinned dual-peer adopters in two languages are not added
  as journey fixtures. In their place, before each tag the candidate is bumped and proved on
  disposable copies of the governed repositories, and the result joins the release evidence. Once
  the bump operation exists, this check is an acceptance of its preview.
- **Rows without gate text.** Three leave 0.2.0: the Skill install operation, the CI carriers and
  the install smoke's check of an absent predecessor. One is kept, the single owner of record
  roots, because it lowers the cost of the bump from which the soak counts. Homebrew keeps the one
  attempt that DR-0021 allows, in the frozen batch. The second landing of the history rebuild
  follows 0.2.0 as its first Change; DR-0024 states that it gates no candidate, and the owner
  confirmed the order knowing that two adopters' rewrites wait with it.
- **What the candidate names not qualified.** MCP, the SDK, the Skill, the CI carriers, Windows x64,
  and Homebrew if its attempt fails.
- **Order and dates.** Four weekly batches end in a frozen beta on 2026-12-12. The breaking changes
  and the agent path land one batch earlier, so agents use them for a week before the freeze. The
  candidate follows on 2026-12-19, or on 2026-12-26 if one batch slips, and the stable release
  seven days after it. When a week slips, the rows that only lower a cost leave first; then the
  release time budget and R11's diagnoses, each by a recorded waiver; then Homebrew, which
  DR-0021 already lets move.
- **The measure.** Progress is the number of gate rows left, 42 on 2026-11-14: 39 required and
  three that lower a measured cost. Each weekly batch reports it, and a session other than the
  author's reads it. The number of closed Changes is not the measure.

## Alternatives Rejected

- **Cut the list to about thirty rows by reading the gate again:** rejected because the gate's
  words require 42 of the 51 rows, so a shorter list takes waivers that the review could not
  recommend.
- **Waive gate reuse:** rejected because reuse is its own sentence of R5, it is what makes a
  pin-only bump cheap, and without it one failed gate in a batch of five Changes costs a full proof.
- **Waive the released entry for CI commit trust:** rejected because it is small, it returns tools
  lines, and it ends the one source build of ETHOS that an adopter's CI still runs.
- **Keep delegation authority in 0.2.0:** rejected because the sized work passes the test ceiling
  at that row, and its CLI case stays caller-asserted in any case until a DR-0006 successor names
  an approval principal that the executor cannot reach.
- **Qualify MCP for 0.2.0:** rejected because that needs the delegation model and a real-client
  test, and an agent with a shell loses nothing by using the CLI.
- **Rebuild the two adopters' history before the candidate:** rejected by the owner because it takes
  a weekly batch and a product budget step and moves the candidate by at least a week.
- **Freeze after three batches:** rejected because it put the agent path and the breaking changes
  in the freeze week, where no agent uses them before the soak, and its dates, 2026-12-08 to
  2026-12-12, allowed no slipped week.

## Consequences and Boundary

- 0.2.0 states two limits wherever it states its position: a proof is self-attested, and
  authorization is caller-asserted.
- The authorization argument changes in 0.3.0, after a stable release, and is named breaking there.
- An agent that needs MCP effects in 0.2.0 has them enabled by the person who launches the server.
- The first test of the two waived adopter shapes on published bytes is the soak's own bump.
- The dates need about two rows closed each working day, four times the rate measured from
  2026-11-08. Preparing each row as a patch in parallel, with the lane landing three to five per
  proof, is the method meant to give that rate; it is not yet measured.
- A later waiver, or a row that leaves, is a successor record that names this one. Records are not
  edited after acceptance.
- This record adds no checker. The weekly order lives in the `rc-scope-plan` design, and the
  terminal plan points to both.

## Evidence and Revisit

- The committee's resolution of 2026-11-07 is the source of the items; it is a local document, and
  this record is its tracked form by shape. The review's fact table quotes the gate's words for each
  of the 51 rows. A verifier found the three blocking findings resolved in the second draft.
- The owner approved the three waivers, the choices for the rows without gate text and the dates on
  2026-11-14, in these words: `按照你建议的方式`.
- The sizes behind the budget claims are the plans' estimates, and fifteen kept rows had none on
  that day.

Revisit when a weekly batch slips, when a budget review changes what fits, or when a DR-0006
successor exists. Retire this record when 0.2.0 has shipped and its release entry states the forms
that are not qualified.
