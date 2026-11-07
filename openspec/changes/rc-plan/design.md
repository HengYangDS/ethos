# Design

## Context

The 2026-11-07 expert committee converged at 16:24 on a resolution
(`build/runtime/work/committee-20261107/resolution-r3.md`, "the resolution"): its §7 sets the gate
for the first 0.2.0 release candidate, and its R6 requires that the plan live in its owners now. At
16:59 the owner accepted the six recommendations of the committee's final report (`final-report.md`
beside it), among them the gate, Windows x64 out of 0.2.0 through a DR-0015 successor, Homebrew only
if its delegating leg passes, and an RC that states CLI authorization as caller-asserted; at 18:18
the owner delegated three more decisions (B.9).

The designs that realize the gate converged in seven drafts under `build/runtime/work/`, which Git
ignores (`.gitignore:5`). Appendices A to G condense them, and Appendix H maps the 30 rows of the
11-05 defect register (`build/runtime/work/beta2/essential-fixes-20261105.md`). The terminal plan
owns dependency order and leaves progress to active Changes
(`docs/plans/terminal-governance-product-design.md:49-52`), no temporary file may become an active
backlog (`:432-437`), and the plan names no 0.2.0 RC order today.

At `ff0c09beb` (dev, 2026-11-07 17:24) no Change is active, and R3 (`layout-invariant-budget`,
archived in `bff918337`) and R7(a) (`absent-consumer-liveness`, archived in `ff0c09beb`) have
landed. R3's lane measured product 73,163 of 75,000, tests 95,657 of 100,000 and tools 8,300 of
10,000 line-equivalents (LE) at 17:14:18 (its task 1.3). Code citations were re-read at `ff0c09beb`;
each appendix names the commit its draft cites, and specification requirements are cited by name
with their line at `ff0c09beb`.

## Goals / Non-Goals

Goals:

- Put the 0.2.0 RC order into the terminal plan as dependency order, not progress.
- Keep each converged design in a tracked, reviewed carrier that later Changes cite.
- Retire the defect register: each row gets an owner Change, a 0.3.0 or host owner, a closing
  commit, or its withdrawal.
- Give the items that R6 names their owners.

Non-Goals:

- Implementing any Change of the order, or changing a specification, test, code path or budget.
- Replacing a later Change's own proposal, design, spec deltas, tasks or acceptance: each later
  Change re-reads its appendix against its own base and owns the decisions it implements.
- Designing what no draft designs (R5, R8(b) to (d) and (f), R11, R12 and the CI carriers), which
  the order names with working names; ordering 0.3.0 beyond what the resolution assigns to it;
  reopening an owner decision.

## Decisions

### 1. One archived Change carries the order and the designs

This Change adds the RC order to the terminal plan (task 1.1) and keeps the details and the
condensed designs here; after archive, each implementing Change cites its appendix in its own
proposal and design. An archived Change keeps history, not current instructions
(`openspec/config.yaml:76-78`), so the one durable cross-Change ruling, the order, moves to the
terminal plan, and each implementing Change adopts its appendix as its own design. Alternatives:

- R6's form, a proposal-stage Change per converged design, keeps at least seven Changes active for
  weeks without progress, and until `change-selector` lands every prewrite among several active
  Changes needs `ETHOS_CHANGE` (`docs/reference/command-plane.md:467-469`).
- A decision record per design holds rationale, not implementation design
  (`docs/decisions/README.md`).
- Leaving the drafts in place is what the terminal plan forbids (`:432-437`).

### 2. The 0.2.0 RC order

The families are in dependency order. A Change waits only for the Changes it names; Changes of later
families that touch disjoint owners may proceed in parallel lanes, while mutation of one owner stays
serial (terminal plan `:366-369`). Each entry gives its source (an appendix Change such as A3, or a
resolution item) and its size as product/tests/tools in LE, each design's estimate (inference).
"Unsized" means that no design gives a size, so the Change declares its growth (R3); a working name
marks a Change that no converged design defines yet.

**Family 1. Measure, plan and scope (R3, R6).** `layout-invariant-budget` (R3) is on dev
(`bff918337`), and `rc-plan` (R6) is this Change. `change-selector` (A1; +40/+60/0), first among
R1's Changes (R6), and `dr-0015-successor` (B1; 0/0/0), the 16:59 scope (B.6), have no
prerequisites, nor does `channels-decision` (R6; 0/0/0), which records the 11-05 channels decision
as DR-0020, the lowest number free on dev: channel model C for 0.3.0, a declared local clean-room
venue that counts once the journey is hermetic, and the hermetic journey as a prerequisite of the
0.3.0 channels, not "the first" (resolution §1, item 5). `product-budget-step` (A2; −60/−40/0)
precedes A3: it retires proved duplication, then raises the product ceiling to 80,000 under a fresh
DR-0010 necessity review.

**Family 2. Application package and catalog (R2's RC scope, R10).** A spike in owned scratch, which
is no Change, drives `land` preview, apply and closeout through the generic CLI adapter.
`application-package` (A3; +90/+60/0) follows A2 and the spike; `next-readers` (A4; 0/+40/0) has no
prerequisite; `catalog-root` (A5; −150/−150/0) follows A3; `catalog-groups` (A6; −250/−250/0) and
`environment-entry` (A7; +110/+170/0) follow A5; `gap-codes` (A13; +80/+80/0) and `provider-ids`
(A14; +50/+60/0) follow A6.

**Family 3. Retention and lane residue (R7).** `absent-consumer-liveness` (R7(a)) is on dev
(`ff0c09beb`). `store-retention` (D; unsized) follows A3, since its verb is born in the application
package (Decision 5), and `next-wire-shape`, already on dev (`c712216d9`); `residue-class` (E; tests
about +40 after a densification) follows D. So does `proof-output-scratch` (working name; R7(b);
unsized): proofs write gate evidence and artifacts to owned scratch or their owner stores within D's
byte budgets, and adopter gates keep their environment and bytecode in the attempt's scratch (E.2,
item 10).

**Family 4. Proof environment, throughput and the shared host (R8(c), R5, R11, R12).** First,
`host-reservation` (working name; R12; unsized): guest vCPUs fit inside the reservation, which caps
only ETHOS's own workers (`src/ethos/adapters/gates/host_admission.py:58-60`), renders run under
`ethos host run`, scratch carries an owner mark (`openspec/specs/quality/spec.md:1883-1888`), and a
tracked CI guest runbook holds no guest address or token value. `gate-environment` (working name;
R8(c); unsized) follows A7 and precedes A10 and MCP `prove`: proof gates run in an allow-listed
environment without SSH agent or forge tokens, or the PDC states the non-sandbox boundary, and one
owner redacts persisted failure output. R5's Changes (working names; unsized) follow
`host-reservation` and A3 (inference): `reference-workstation` declares the reference host by
hardware class and reports time per gate; `fast-tier` adds architecture and import-selected tests to
readiness; `gate-reuse` splits `unit-architecture`, keys reuse on every file a gate reads and keeps
one coverage floor decision per attempt (MODIFIED `openspec/specs/quality/spec.md:120-131`); the
900-second requirement is then met, or amended with the measurements. R11's items (working names;
unsized): the `test_gate_policy` file-missing error and the exit-130 interruption are diagnosed; a
macOS proof across 03:35 passes with `32d94043c` (owner 97f828; next window 11-08 03:35);
`coverage-floor-gap` gives the floor its own gap code; `build-audit-offline` stops `build` waiting
on the networked vulnerability lookup, which stays blocking in proof and release.

**Family 5. Lane operations, run handles and authorization (R1, R8(a)).** After A6 come
`hook-install-converge` (A8; +30/+120/0), `hosted-observation` (A11; +300/+250, tools with A17),
`skill-install` (A15; +120/+100/0) and `run-handles` (A10; +340/+310/0), which also needs
`gate-environment`; after A6 and A7, `delegation-authority` (A12; +420/+340/0) and `lane-operations`
(A9; +600/+490/0), which also needs Family 3. The CI carriers (agenda B item 3; undesigned,
unsized), a GitHub Action and a GitLab CI component that carry `ethos prove --host` for the pinned
release, follow A6 and precede A16; the GitLab component is not qualified for 0.2.0 (B.6).
`mcp-projection` (A16; +260/+230/0) follows A10 and A12, and MCP `prove` comes only after
`gate-environment`, otherwise the RC labels MCP a preview.

**Family 6. Supply security and fleet hygiene (R8(b), (d), (e), (f), R9).** `release-provenance`
(working name for R8(b)'s workflow Change; unsized) precedes C1 and B11: tag-ref dispatch in a
protected environment with inputs through `env`, immutable releases, a CI supply image bound only
when its provenance names `refs/heads/dev`, post-tag defects shipped as a new prerelease in the
tag's batch, and a matching change to `docs/guides/release-and-publication.md:23`.
`secret-scan-supply` (working name; R8(d); unsized) resolves the secret scan through locked supply
and reports it unarmed without a policy. `evidence-ref-scan-scope` (register row 12; R9; unsized)
excludes `refs/ethos/*` from every history scan that ETHOS ships and renames digest-valued payload
keys that look like credentials. `npm-retirement` (working name; R8(f); unsized) retires
`distributions/npm` (`distributions/npm/bin/ethos.mjs:73-87`) before B11, which names its
`package.json` as a version carrier (inference). `peer-identity-records` (F; unsized) follows A3,
with `peer-resolution` on dev (`b6f6b973c`), and `history-rebuild-map` (G; unsized) follows F; for
R8(e), ETHOS runs G's readiness scan over its own declared refs once and records the disposition,
while the rebuild applies serve two adopters and gate no RC (inference).

**Family 7. Release path (R4, `github-pin` step 2, R9, R10, agenda A).** `github-pin` (C1;
+60/+80/+60) follows `release-provenance`, and `pin-selection` (C2; +185/+185/0), `adopt-pin` (C3;
+55/+60/0), `release-acceptance` (C4; +120/+110/0) and `http-retirement` (C5; 0/−40/−60) follow C1.
C1 to C4 ship in one release R, each adopter pins in its own Change after R, and R10's one install
line per host lands with C3, and with C6 where Homebrew qualifies; `brew-channel` (C6; +20/+40/+30)
follows C4 and enters 0.2.0 only if its leg passes. After C1 come `hermetic-journey` (B2;
+10/+220/+260), then `journey-fixtures` (B9; 0/+60/+170), and with A3 `release-predecessors` (B3;
+140/+120/−30), then `predecessor-smoke` (B5; 0/+40/+60); `full-suite-legs` (B4; +30/+40/+30) has no
prerequisite. `release-rehearsal` (B6; 0/+190/+240) follows B2, B3 and B4; `rehearsal-admission`
(B7; +200/+170/0) follows B6 and A3; `rollback-after-repair` (B8; 0/+80/+130) follows B2 and C2;
`journey-hosts` (B10; 0/+10/+10) follows B1 and B2; `stable-release-path` (B11; +80/+80/+45) follows
B6, B7, `release-provenance` and `npm-retirement`; `release-time-budget` (B12; 0/+15/+20) follows
the first rehearsed release.

**Family 8. Golden path, soak and promotion (R1's acceptance, §7).** `golden-path-journey` (A17;
0/+230/+650, the tools with A11's) follows A4, A8 to A16 and B6, and after its acceptance 3 the
operator kit retires (Decision 4). Release Changes follow D19: one per weekly batch, a fix beta only
for a defect that blocks landing, corrupts an installation or admits a wrong proof, and adopter
bumps once per batch. The soak runs on one frozen beta whose journeys pass on every declared host,
whose golden path passes, and which adopters' accepted pins and proofs name, for 72 hours from the
last landed adopter bump; only D19-exception fixes land until 0.2.0 ships (B.9), and a new operator
kit script restarts the 72 hours. The RC re-versions the soaked beta
(`docs/decisions/dr-0015-release-stage-scope.md:42`) through B11's promotion check and inherits only
its use period and defect record; its entry names every unqualified form and channel, Windows x64
included, and states that CLI authorization is caller-asserted (owner decision 6). Stable follows
after 7 days (`openspec/specs/distribution/spec.md:732-737`).

The order holds about 53 open Changes besides this one and the release Changes; the resolution
estimated 40 to 50 (§7).

### 3. Budget

From the measured base, the sized Changes add product +2,880 (A +1,980, B +460, C +440), tests
+3,560 (A +2,100, B +1,025, C +435) and tools +1,615 (A +650, B +935, C +30) (inference). Product
would reach about 76,040, so A2's step to 80,000 precedes A3 and leaves about 3,960 for the unsized
Changes. Tests would reach about 99,220 of 100,000, leaving about 780 for D, E, F, G and every
unsized Change: one densification serves the queued Changes together, and if the measured need still
exceeds the freed space, one 5,000 step is taken with that evidence under DR-0010 (E.2, item 9).
Tools would reach about 9,915 of 10,000, so their ceiling binds Family 7 and A17 (inference).

### 4. Owners for R6's items

- `fast-tier`, selection from recorded facts
  (`openspec/changes/archive/2026-11-01-test-runner-unification/design.md:181`), is Family 4's,
  `test-tiers`, arming the tier guard (`:57`), is 0.3.0 with R11's other items, and
  `release-prepare`, the order session at the release (`:57-58`), joins B4, because the per-release
  suites run inside the rehearsal (resolution R4); 97f828 owns all three, and the last placement is
  this design's own.
- Kit-created Keychain items: owner 97f828. Before A17 retires the kit, an inventory by service and
  account metadata, never a value, names each item's consumer.
- R11's proof across 03:35: owner 97f828, next window 11-08 03:35. The 11-05 channels decision:
  `channels-decision`, DR-0020. Left to 0.3.0: PyPI's account and first upload (owner decision 2)
  and the approval principal of a DR-0006 successor (owner decision 6; A.8).

### 5. Where the resolution amends a draft

D, E, F and G predate the committee. Where a draft and the resolution differ, the resolution holds
and the implementing Change carries the amendment:

1. R1 has every new operation born in the application package, never in `surface/cli`, so D's and
   F's verbs are entries in `ethos.application`, D and F follow A3, and D's destructive apply takes
   the catalog's authorization rule once A12 lands (A.9, Breaking change 1).
2. R7(c) needs byte budgets and a 48-hour observation, which D does not design. D adds them for its
   owned kinds, the owner stores that `proof-output-scratch` writes to and the host store's runtime
   copies (C.1, item 7), and carries R7(a)'s explicit release of an absent consumer, which
   `absent-consumer-liveness` left to it.
3. R7(b) has two halves: E records checked residue and lets `retire landed` remove it, and
   `proof-output-scratch` keeps evidence and artifacts out of lanes; kits are R6's, and A17 retires
   them. The channels decision planned DR-0018 and G's record DR-0019, both taken on dev
   (`docs/decisions/README.md`), so both take free numbers.
4. Owner decision 4 narrows R4's "Windows full suite timed and triaged first": B runs the Windows
   x64 suite non-blocking and timed and moves its triage and the Windows journey to 0.3.0, which B1
   records.
5. Agenda A admits the Mise pin "with attestation verification" once task 1.1 verifies beta.6 on all
   five platforms, as the final report read it at 16:3x; C is stricter, keeping adopter claims at
   `checksum` until C1's negative cases pass under CI's Mise, and the RC's channel row follows C1.
6. R10's install line names an attested channel, so it lands with C3 rather than A4; R9's "`status`
   reports adopter lag" lands with B3's stepped path; and Decision 3 uses step 2 draft 3's +440
   product, where A used an earlier draft's +280.

### 6. The register retires into Appendix H

Appendix H gives each register row one disposition. After this Change the register is no input: a
later defect reaches its owner Change, a regression or an existing rule (terminal plan `:432-437`),
and the register's ignored copy is deleted after archive (Workflow follow-up).

## Risks / Trade-offs

- R6's wording: R6 makes each converged design a proposal-stage Change or defers it in a decision
  record. This Change reaches R6's ends (tracked designs, one lane, one proof, a retired register)
  in another form, which R6's owner, 97f828, accepts with this Change or replaces with the
  proposal-stage Changes.
- Reviews: R6 has each draft's reviews move with it, the 12 under
  `build/runtime/work/fbee0c-session/reviews/` included. The appendices keep each review's outcome
  but no review text, so the drafts and reviews stay until the owner moves the reviews, after the
  private-address scan, into this Change or each implementing Change.
- Condensation and staleness: the appendices keep each draft's decisions, Changes and acceptance but
  drop most rationale, citations and test detail, against drafts that cite `c3ca98963`, `bfaa87543`
  and `727ee0579`. An implementing Change re-reads every citation at its own base and restates the
  decisions it implements (`openspec/config.yaml:76-78`).
- Budgets and schedule: tests keep about 780 LE and tools about 85 after the sized Changes (Decision
  3), so a test step and tools cuts are likely; about 53 Changes against the resolution's 40 to 50
  put its RC estimate, 11-18 at the earliest and 11-20 to 11-25 realistically, at risk (inference).
  Undesigned Changes may also split or merge in their own designs, since the order fixes only their
  dependencies.
- Length: this design is one review unit of about 1,100 lines; linked semantic subdirectories
  (`openspec/config.yaml:61-62`) are the alternative if review needs them.

## Appendix A. Operation catalog (R1, R2, R8(a), R10)

Source: `build/runtime/work/operation-catalog/design-draft.md`, draft 2, converged 11-07 18:3x after
the reviews of M1, M2, M3 and M5; its citations at `c3ca98963` hold at `ff0c09beb`. Sizes and
prerequisites are in Decision 2.

**A.1 Package.** `ethos.application` sits between the surfaces and `domain` and owns every public
operation and the catalog: `invocation.py` is the one entry (environment entry, deadlines, handles,
lazy implementation import, failure normalization, console re-execution), and `catalog/` has one
module per group. `prove` moves first, since only the CLI owns it today
(`docs/reference/command-plane.md:123`), then the orchestration modules of `domain` and the thin
bodies of `surface/cli`. The import-linter layers
(`.config/checks/import-linter/import-linter.toml:10`) gain `application` between `surface` and
`domain` with three `forbidden` contracts: surfaces and `ethos.cli` import none of `domain`,
`adapters`, `repository`, `normalization` and `assistants`; `ethos.contracts` and `ethos.result`
import nothing above them; `domain` imports no `adapters`. Today's imports start as
`ignore_imports`, emptied by A5 and A6 for surfaces and by 0.3.0's typed Facts for `domain`, and a
static rule resolves every implementation under `ethos.application`.

**A.2 Catalog.** Each operation has one entry under a stable `<group>.<operation>[.<mode>]` ID such
as `land.closeout.apply`: a kernel-facing half as data in `ethos.contracts.operations` (CLI path and
selectors, effects, `destructive`, exit kind, inputs, and an authorization kind among `none`,
`apply`, `authorize`, `confirm-irreversible`, `delegation` and `human`) and an application half
(summary, request model, `call` or `handle`, deadline, MCP exposure, implementation). Preview and
apply are separate entries, and the 42 leaves become about 85. A table-driven test holds the static
rules: halves pair one to one; IDs are unique; every field is described; selections per CLI path are
disjoint and total; a write needs a kind other than `none`; remote-write, release or destructive
needs `delegation`; `opaque` needs `human`; a deadline above `timeout.request_seconds` needs
`handle`; nothing that writes a remote or signs is a `handle`. The 14 destructive argv rows
(`src/ethos/contracts/admission.py:130-145`) retire.

**A.3 Typed steps and `next`.** Producers return typed steps, which the CLI renders as
`next_action`; A5 and A6 convert the golden path's builders and A13 the rest of the 157 builders and
218 sinks, and until 0.3.0 the kernel derives `next` from `next_action`
(`src/ethos/result.py:115-120`) through the catalog, an unselected argv being `opaque` and `human`.
`next.form` is the operation ID, `next.binding` the complete validated request plus
`actor = "executor"`, and `next.inputs` each value that only the agent can choose, since a
placeholder makes `next` argv-less (`src/ethos/contracts/next_step.py:80-82`). A `decision` is
`human` and carries the argv a person approves. A failed gate continues to the evidence-only
`prove --host --execute --gate <id>`, which for a test gate reruns only the failing tests that its
provider reports; a holder mismatch continues to handoff or reacquire. A `next` equal to its own
command is a loop, except `run.wait` and `publish.hosted.observe` before their deadline.

**A.4 Projections.** A generic CLI adapter builds one Cyclopts command per path from its entries'
request fields, the bound selectors picking exactly one entry or exiting 2 with
`command_operation_unmatched` (JSON under `--json`); help comes from the field descriptions,
`ethos --help --json` prints the catalog, and the 42 leaves retire. MCP has one tool per exposed
entry, binding `root` and the actor at startup, with hints from the entry's effects (read-only for
`read`, `remote-read` and `local-evidence-write`, destructive from the entry, idempotent where a
retry reports the original effect, open-world for remote effects); effect tools need
`--enable-effects` (R8(a)). The SDK is excluded from the RC; conformance fixtures call
`ethos.application.invocation.invoke`, which refuses with `sdk_runtime_not_selected` when `CURRENT`
names another build. Gate providers resolve by catalog ID, such as `provider.docs-registry`, not by
module path (`src/ethos/contracts/gates.py:175-182`), and a packaged data table, not a Python alias,
maps each legacy `ethos.*` name, the adopters' included, for one R9 support window.

**A.5 Lane operations.** `lane start --change C` is the one entry into work: it names the lane after
C, creates C through the embedded official OpenSpec and makes the actor the holder;
`lane new-change` adds a Change, `lane prewrite --change C` takes its paths from `next.inputs` over
`ETHOS_CHANGE`, and `lane commit --change C` checks format, prose and projections, stages exactly
the authored and generated paths and commits with a subject derived from the Change.
`lane environment` runs each profile's environment task as a handle, the archive entry first
validates every spec strictly on owned scratch, `publish --observe-hosted --expect-head H` records
one hosted-plane Attestation per CI peer, `skill install` links each host's skill directory through
the build that `CURRENT` selects, and `host run` takes the run deadline. Each `next` binds root,
heads, receipt, Change and plan digest, so the kit's chains become one loop: archive, a detached
full proof, `run wait` and `land`; closeout where the actor's delegations cover the accepted ref,
else the proposal ref; `lane environment` and `hook install` on a self-hosted accepted root;
publication of `dev` to every peer; the hosted observation and then the release ref, since closeout
already moves local `main` (`src/ethos/adapters/mutation/accepted/promotion.py:100-111`);
`lane retire landed` with declared residue. Chain verbs are rejected, and each of the hardening
kit's 32 scripts maps to an operation or to nothing.

**A.6 Run handles.** `--detach` writes a receipt (operation, request, actor, head, deadline) under
`<git-common>/ethos/runs/<id>/` before any effect, and a repeated start attaches only when the
digest matches and the runner's lock is live. Proof runs, `lane environment` and the non-release
`land` and closeout applies are handles; `land --release` and retag stay calls, because they sign
tags. The runner (`python -I -m ethos.application.run.runner <receipt>`) starts in a new session
with closed stdin and R8(c)'s allow-listed environment and runs the operation in process, holding
the proof slot (`src/ethos/adapters/gates/proof_slot.py:161-177`) and the host ticket itself.
`status` lists live runs in `data.runs`, `run wait --timeout S` returns the operation's result,
`run cancel` reports `cancelled` or, when an effect may have begun, `unknown`, and liveness is the
pid with its lock; `timeout.run_seconds` (bound 14,400) bounds runs, and MCP starts handles within
each call's deadline (`src/ethos/surface/mcp/server.py:49`).

**A.7 Environment entry.** `invocation.py` reads the process once. The actor is the executor's own
identity, from `--actor` wherever `binding.actor = "executor"`, else from the declared fallback
`ETHOS_ACTOR`, and MCP binds it at startup; a missing actor yields an `instruction` whose `inputs`
name it, and a mismatch continues to handoff or reacquire, never to an `export`. The Git
configuration overlay reaches local Git only, with only the keys that `system/surfaces.toml`
declares, starting with exact-path `safe.directory`; network Git and signing get none, other keys
are dropped and named in `summary.environment`, and other children get no overlay, no `VIRTUAL_ENV`
and closed stdin.

**A.8 Authorization.** Today `--authorize` is a flag check
(`src/ethos/domain/publication/request_gaps.py:84`), and `--authorization` parses an Attestation
(`src/ethos/surface/cli/lane/lease.py:271-272`), which mints no authority (PDC:108). A `Delegation`
(`id`, `repository`, signed `catalog` digest, `actor`, `operations`, `refs`, `peers`, `expires_at`,
`approver`) lives in `.ethos/delegations/<id>.toml` with its SSH signature, read from the accepted
ref's tree and cited by ID; class grants hold only under its catalog digest, absent `peers` means
none, and release and destructive operations need explicit IDs. Approver keys sit in an anchor kept
like the commit trust anchor and never equal a configured commit signer. `delegation.propose` writes
the file in a lane, `delegation.sign` is a `human` decision run with the anchored key, and
`delegation.revoke` narrows at once through a local record read at effect time. A covered step
carries `--authorization <id>` and `--expect-plan-digest`; an uncovered one is `await-user` on the
plan digest, with `data.approval` saying why each delegation misses. The effect's Attestation
records `client-confirmed` for an accepted MCP elicitation, `independent` for a signer that a
DR-0006 successor declares independent (0.3.0), else `caller-asserted`, the RC's CLI case, never
above the landing that admitted the delegation; changing `.ethos/delegations/**` makes `land` and
closeout `await-user`. Over MCP every gated apply elicits from server-derived values, a client
without elicitation gets `await-user`, each host qualifies by the real-client refusal test, and no
ETHOS projection writes `--enable-effects`.

**A.9 Compatibility.** Expand, then contract (`openspec/specs/distribution/spec.md:695-701`):
`ETHOS_CHANGE` and `--holder-ref` stay for one window, readers accept `delegation` and `inputs` a
release before producers emit them, legacy provider names map for one window, and text-derived
`next` stays until 0.3.0. Named Breaking: (1) remote-write, release and destructive continuations
await a person unless a delegation covers them; (2) `--authorization` names a delegation ID, the
kind `attestation` becoming `delegation`; (3) usage exits 2 with JSON, undelivered 3 (was 1), a
`host run` refusal 125 (was 1), a committed archive awaiting proof 0 (was 1), a `publish` probe on
`unknown` 1 (was 0); (4) `hook install` deletes nothing, reclamation moving to `hook retire-supply`;
(5) continuations drop `export ETHOS_ACTOR=` and `--holder-ref`; (6) MCP tools take catalog names,
and effect tools stay off unless enabled at launch; (7) a failed gate continues to
`prove --host --execute --gate`; (8) the release ref needs a passing hosted observation on each CI
peer. `ethos prove --host --execute --full --json` keeps 0 on `pass` and 1 on `block` or `unknown`,
which a conformance fixture pins.

**A.10 Acceptance.** (1) Hosted golden path: an unadopted two-peer fixture repository, one peer a
fixture forge whose stub `gh` reports CI runs for exact heads, a delegation signed by a fixture
owner key that the job lacks, and published bytes installed through the Mise pin. A deterministic
executor without a model starts at the `adopt` preview, adds `--actor`, runs `next.argv` only for
commands of kind `none`, `apply`, `authorize` or `delegation`, supplies `next.inputs` and fixture
edits from its script, and checks each carried `next`, the budgets, the exits and the end state
(lane retired, `dev` and `main` equal on both peers, runtime current); without the delegation it
stops at `await-user` before any remote write, after `delegation revoke` the next gated step stops,
and one run sets an allowed and a dropped overlay key. (2) The same journey on a self-hosted root,
both in B's rehearsal. (3) One real ETHOS Change runs from start to retirement through `next` alone,
with lane environment setup, a focused `ethos host run` and B's release readback, and the kit then
retires. (4) A detached proof's runner survives its launching process group and holds the proof slot
and host ticket under its own pid. (5) Catalog-driven fixtures give identical verdicts through the
installed console and a real MCP client, diffing refs, index, worktrees and Git-common state for
write entries.

**A.11 Changes.** (1) `change-selector`; (2) `product-budget-step`, whose DR-0010 necessity review
retires proved duplication (43 `ETHOS_ACTOR` reads into one owner, seven 64-hex checks into one
digest type, the dead `mapped_retag_receipt`) before the product step to 80,000, which the owner's
2026-11-01 rule delegates to the agent with evidence; (3) `application-package`; (4) `next-readers`,
with a test that refuses text readers; (5) `catalog-root`, the root operations, exits, JSON usage
errors and help, with a MODIFIED `Public Command Plane` (`openspec/specs/command-plane/spec.md:10`),
PDC:366 and the module-layout rule; (6) `catalog-groups`; (7) `environment-entry`; (8)
`hook-install-converge`, ending the `hook install` self-loop; (9) `lane-operations`; (10)
`run-handles`; (11) `hosted-observation`, with the fixture forge peer; (12) `delegation-authority`,
through model promotion; (13) `gap-codes`, the gap registry as data, the exit table, the remaining
builders and the fixtures; (14) `provider-ids`; (15) `skill-install`, on one real agent host or not
qualified; (16) `mcp-projection`; (17) `golden-path-journey`. 0.3.0: `sdk-stability` (+80/+150),
`text-next-retirement` (−150/−100), `typed-facts`, `git-port` and `typed-seams`.

**A.12 Admission and gaps.** Under PDC:347-357 the catalog and the delegations are admitted because
without them "CLI, SDK, MCP and Skills expose the same capabilities" and "approved by a principal
other than its executor, and not revoked" are unprovable, Attestations minting no authority; the run
receipt is already required by PDC:394-401, owned by run handles and budgeted by R7(c). Open:
overlay keys beyond `safe.directory`, a stub `gh` for the forge peer, and owner decision 6's
approval principal (0.3.0). Unproved: Cyclopts union flattening and JSON usage errors under Cyclopts
5.3.3, FastMCP elicitation and hints, import-linter's layer semantics, and the sizes.

## Appendix B. Pre-tag release rehearsal and the stable path (R4)

Source: `build/runtime/work/release-rehearsal/design-draft.md`, revision 2, after the reviews of M4,
M6 and M7, their confirmations of 18:3x and the owner's decisions of 16:59; it cites `c3ca98963`.
Sizes and prerequisites are in Decision 2, Family 7.

**B.1 Rehearsal.** A `workflow_dispatch` of `ETHOS CI` with a new `rehearse_head = H` input, passed
through `env`, runs on GitHub, by default on the release lane's proposal ref right after
`ethos publish` of the archived, locally proven head, so a failed candidate never reaches `dev`; its
jobs refuse unless `github.sha` is H and `v<VERSION>` does not exist. Its jobs, generated in
`pipeline.cue` from the release jobs' declarations, are `rehearsal-platforms` (the five release legs
with `--rehearse --expect-head H`, whose audit blocks an advisory); `rehearsal-assets` (`assemble`
in rehearsal mode, writing `SHA256SUMS`, `left-out.json` and notes, never attesting or publishing);
one `rehearsal-journey` per declared host (hermetic and clean journeys, each predecessor's upgrade
with restore-then-rollback, A's golden paths and the brew leg if Homebrew is in); `rehearsal-suite`
(B.2); and `release-rehearsal`, which passes only if every required leg passed. With
`contents: read` and `attestations: read` only, a rehearsal mints no attestation; it builds release
identity when the checkout is clean at H, H's signature passes the commit trust, the version has no
tag and the entry passes the release tag policy. The candidate installs offline from a `file://`
table checked against `SHA256SUMS`, predecessors through `github:` with `locked_verify_provenance`,
each leg for its own platform, and both must resolve the same `bin` and `runtime/<16 hex>` paths.
The receipt binds H, tree, version and workflow blob, per-platform digests or left-out causes, each
journey step's verdict per predecessor and class, each suite leg's verdict, counts, coverage, skips
and time, and each job's attempts. A release operation born in the R2 package (working name
`ethos release rehearsal --head H`) reads the newest completed rehearsal for H from the GitHub peer,
checks bindings, predecessor set and verdict, and records a non-authorizing `release-rehearsal`
Attestation; the offline `land --release` otherwise refuses with `release_rehearsal_unproven`, and a
newer failure is never outvoted by an older pass. Adopters opt in with
`[release.rehearsal] peer = "github"` in `.ethos/release.toml`, which `product-boundary` requires of
ETHOS itself.

**B.2 Suites and budget.** Linux x64 with Python 3.12 and 3.13 blocks the tag, and Windows x64 with
3.14 runs non-blocking and timed; with hosted Linux arm64 and local macOS on 3.14, every OS, both
architectures and the three Pythons run once per release. Suite legs record coverage without the
floor, since `fail_under = 95` (`.config/checks/coverage/coverage.toml:9`) would block a leg on
coverage alone, and a quality delta keeps one floor decision per proof attempt. Every proof's
`local-install-smoke` upgrades from the previous release through `--predecessor-runtime`
(`tools/ci/sessions.py:184-195`), and an absent previous release makes it `unknown`
(`predecessor_runtime_absent`), never a pass. B12 budgets four spans, S1 the rehearsal, S2 tag-ref
dispatch to publication (76 minutes for beta.6), S3 publication to the last journey and S4 release
proof to qualified, from the first rehearsed release, rounded up to 15 minutes; an overrun is a gap
that the next release Change cuts or amends with measurements. Estimate (inference): S1 110 to 125
minutes, S3 15 to 40 minutes, S4 5 to 6 hours.

**B.3 Predecessors and restore-then-rollback.** Adopters are the live consumers that the host store
records (`src/ethos/adapters/repo/runtime/materialization/host_retention.py:58-64`), less the
producer; an absent consumer is unknown and refuses, with R7(a)'s explicit release as `next`, and a
repository leaves only by a completed exit. The set, through a MODIFIED
`A beta's journey starts from every release that adopters select`
(`openspec/specs/distribution/spec.md:827`), is the previous release plus the releases that each
adopter's accepted-branch pin and `CURRENT` name; a `CURRENT` that names no published release
refuses. The window is two D19 periods (14 days), proposed for R9, and for an older adopter `status`
names the newest release whose recorded `[release] upgrade_from` lists the adopter's release, or
states that no qualified path exists. Classes: `attested`, a tag-ref release verified with signer
workflow `ci.yml` and `--source-ref refs/tags/v<V>`; `attested-main`, alpha.29 to beta.6 except
beta.3, verified with `ci.yml`, `--source-ref refs/heads/main` and `--source-digest` equal to the
commit its signed tag names (DR-0018); `checksum`, the releases before alpha.29, beta.3 and any
digest mismatch. The list is data in C1's pin module. `[release] upgrade_from` in
`.ethos/release.toml` lists releases and classes, never adopters; a catalog operation derives it in
the release lane with each adopter's accepted-ref OID and pin as evidence; rehearsal, release run,
notes and changelog render from it; and `land --release` re-derives it offline and refuses an empty
or incomplete set. Restore-then-rollback per predecessor P extends `prove_retained_upgrade` for C2:
(1) pin P, seed retained state and land a pin bump to the candidate, whose selection repairs the
declaration; (2) `hook install --runtime P --reason <r>` refuses with
`runtime_rollback_declaration_repaired` and changes nothing, and without `--reason` it refuses; (3)
a lane from the accepted tip restores P's declaration, where the command writes the rollback receipt
and the next transition reports `runtime_rollback_open` with `CURRENT` on P; (4) landing the pin
revert deletes the receipt, and a new pin bump re-upgrades, with retained state unchanged
throughout.

**B.4 Stable path and clock.** B11 makes assembler and journey accept `vX.Y.Z`, publishes a stable
release with `--latest`, and gives `land --release` a promotion check: a promotion tag (beta to
`rc.1`, `rc.K` to stable) names its soaked tag, and its diff may touch only the version carriers,
the changelog and one OpenSpec Change directory without spec deltas, else
`release_promotion_source_changed`. Through a MODIFIED
`Release candidates and stable releases follow adopter use`
(`openspec/specs/distribution/spec.md:732`), a promotion inherits only the soaked build's use period
and defect record, runs its own proof, CI, rehearsal, release run, attestations and journeys, and
upgrades from the soaked build. beta.N's 72 hours start after its journeys pass on every declared
host and its golden path passes, counted from the last landed adopter bump; `rc.1`'s 7 days count
alike, and a fix or a new kit script restarts the clock (inference). Dress rehearsals of
`0.2.0-rc.1` and `0.2.0` on scratch proposal refs, never landed, precede the RC.

**B.5 Hermetic journey (B2).** One environment owner gives every child process a fresh HOME and
TMPDIR, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `GIT_ATTR_NOSYSTEM`, empty templates and no SSH
agent, forge token or `XDG_*` variable, with PATH as links to declared executables and a
digest-bound Mise. Acquisition, the only networked stage, fetches the rehearsal artifact or the
published release and the predecessors into a verified manifest; offline qualification re-hashes
before each install, refuses a tampered archive, self-checks before the first child
(`journey_environment_not_hermetic:<what>`) and records the venue. Venue counting, signed local
receipts and Windows beyond the Git variables are out.

**B.6 DR-0015 successor (B1).** Windows x64 leaves 0.2.0's declared journeys for a 0.3.0 focus: its
archives stay optional legs qualified by smoke and inventories, its suite runs non-blocking and
timed, the RC names it not qualified, and the pin gets no Windows role. Homebrew enters 0.2.0 only
if the macOS trial and the delegating brew leg pass: C6 runs the leg in the rehearsal from a formula
rendered from `SHA256SUMS` in a job-local tap, with install, `brew test`, upgrade, rollback and
uninstall on macOS arm64 and Linux x64, on a host whose Mise Homebrew does not own, and on a host
without Mise that asserts the refusal and its `next.argv` `brew install mise`. The GitLab CI
component is not qualified, and Linux arm64 gets the journey leg that DR-0015 declares and
`pipeline.cue` lacks.

**B.7 Consistency.** A defect in the tag's build or publication ships as a new prerelease in its
tag's batch (R8(b)), while a journey-only dispatch may re-qualify identical published digests when
the hermetic receipt binds the journey commit and environment, so `journeyRun` stays. A re-run in
the tag-ref run serves only an infrastructure failure before any ETHOS step, once, never repeating a
succeeded publication job, and R8(b)'s workflow Change lands with or after B6 and B7. The published
`github:` journey stays whole in 0.2.0, and the rehearsal does not replace R11's proof across 03:35.

**B.8 Changes.** (1) `dr-0015-successor`, B.6, a delta to
`Prereleases advance on declared journey evidence` (`openspec/specs/distribution/spec.md:713`); (2)
`hermetic-journey`, B.5; (3) `release-predecessors`, B.3's set, window, classes, carrier and
operation; (4) `full-suite-legs`, B.2's legs and coverage mode; (5) `predecessor-smoke`; (6)
`release-rehearsal`, B.1's jobs, modes, table, layout check and receipt; (7) `rehearsal-admission`,
B.1's observation, Attestation, opt-in and boundary check; (8) `rollback-after-repair`, B.3's four
steps; (9) `journey-fixtures`, pinned dual-peer Python and Go adopters; (10) `journey-hosts`, the
Linux arm64 leg; (11) `stable-release-path`, B.4 with the dress rehearsals; (12)
`release-time-budget`, the spans. 0.3.0: `windows-suite-triage` (product 0 to +300, tests +100 to
+400, tools +40). Not here: A's golden-path driver, which joins B6; C; R8(b)'s workflow Change;
shards; a pre-tag binary scan.

**B.9 Admission, delegated decisions and gaps.** The `release-rehearsal` Attestation is a new
predicate of an existing owner, and release configuration owns `[release.rehearsal]` and
`[release] upgrade_from`, which have no other owner (PDC:347-357). The owner delegated three
decisions at 18:18: (1) GitLab runners keep no stored GitHub credential, install from the lock with
provenance re-verification off, and claim exactly "checksum-verified against a lock entry whose
attestation the bump lane's recorded `mise lock` verified"; (2) the accepted release identity
records every published wheel and archive by digest, through an expand-then-contract schema change;
(3) only D19-exception fixes land during the 72-hour soak and until 0.2.0 ships. Open for the
committee: the host store's consumer record as the adopter source. Unproved: reproducible bytes from
two builds of one head, the `--source-digest` binding of the closed list, the Linux 3.12 and 3.13
suites, the Windows suite's time, and Mise offline from a `file://` table.

## Appendix C. `github-pin` step 2 (R8(b), R9, agenda A)

Source: `build/runtime/work/github-pin/step2-design-draft.md`, draft 3 (18:28), after the reviews of
fbee0c and M4 and the task 1.1 spike (`github-pin/task-1.1-spike-20261107.md`); it cites
`c3ca98963`. Sizes and prerequisites are in Decision 2, Family 7.

**C.1 Decisions.** (1) Backend `github:` with named claims, since `aqua:` needs a registry recipe
and `ubi:` is leaving. Each release has a B.3 class, kept as data in the pin module. An adopter
claims `checksum` until C1's negative cases pass under its CI's Mise, then "checksum-verified
against a lock entry whose attestation the bump lane's recorded `mise lock` verified"; only the
journey and the rehearsal check signer and source, and no claim exceeds what its verifier checked
(PDC:498-502). (2) One pin form, the bare entry that `mise use` writes,
`"github:HengYangDS/ethos" = "<version>"` under `[tools]`, with `locked_verify_provenance = true`
under `[settings]` and no `prerelease`, `asset_pattern` or `bin_path`; every installer, the
`file://` table included, yields Mise's stripped `bin/` and `runtime/<16 hex>`, proved under Mise
2026.10.25. (3) `CURRENT` projects the accepted pin forward only: no implicit transition moves it to
an older release, and a lane-bound selection receipt records every departure. (4) Expand before
contract: a release that retires a declaration form follows one that accepts both, and a
successor-first bind covers the rest. (5) One global owner per host: Homebrew on macOS and Linux
where C6 qualifies, otherwise Mise's global pin and `mise lock --global`; never both; no Windows
role. (6) C4 wires `release_policy_report` and `materialize_explicit_release`, which have no
production caller, as decided on 11-03, and gives the accepted identity every published byte. (7)
The host store owns each selected runtime, and `CURRENT` never names a Mise or Cellar path; Mise's
copies stay within R9's support window and the host store's within R7(c)'s budgets, about 672 MB
each per version. (8) A bump relocks in place, never with `--upgrade`, by the repository's CI Mise
or, where it declares none, by ETHOS's digest-bound CI Mise; it stops if `lockfile_version` changes,
and a format move is its own reviewed step first.

**C.2 Changes.** R8(b)'s workflow Change comes first, then C1 before C2 to C5, and C4 before C6; C1
to C4 ship in release R, and each Change keeps today's behavior where its input is absent.

1. `github-pin`: `release/pin.py` holds the key, the bare entry, readers of both TOML forms and of
   lock entries, and the classes. The journey runs CI's Mise in a scoped home: the Linux x64 leg
   locks five platforms once and requires `github-attestations` on each, each leg installs its own
   platform under `locked_verify_provenance`, `gh attestation verify` takes the class's signer,
   source ref and digest, and the `--repo`-only check
   (`tools/ci/delivery/acceptance/journey.py:193-201`) goes. Done when, under Mise 2026.10.25, the
   bare form locks and installs beta.6 on both legs as `attested-main`, a version-3 relock keeps
   `github-attestations`, the stripped `file://` table gives the same layout, a byte-flipped archive
   is refused at install, and an asset attested only by another repository yields no attestation
   entry or a refusal; a failing negative case keeps every claim `checksum`.
2. `pin-selection`: without `--runtime`, `install_hook_launchers` and `adopt --select-runtime` read
   the pin and its lock entry from the accepted branch, refuse with `runtime_pin_unattested` when
   the platform's entry lacks `github-attestations` outside the checksum class, and pass the
   resolved install on as `installed_runtime`. Transitions select only a newer pin
   (`runtime_pin_behind_current`, with a receipted `hook install --runtime` as `next`); without a
   pin the invoking build runs (the advisory `runtime_pin_absent`); an uninstalled pin leaves
   `CURRENT` in place (`runtime_pin_not_installed`), and ETHOS fetches nothing.
   `hook install --runtime <R> --reason <text>` from a lane runs the preflight against the accepted
   tip's declaration and writes a lane-bound `successor` or `rollback` receipt under
   `<git-common>/ethos/receipts/runtime-selection/`, which keeps `CURRENT` on R
   (`runtime_selection_open`) until the accepted pin changes or the lane retires.
3. `adopt-pin`: the adoption plan writes the invoking release's bare entry and
   `locked_verify_provenance` into `.config/mise/config.toml`; another version or an `http:ethos`
   table is an `adoption_conflict`, a development build plans no pin, and `next` is `mise lock`.
4. `release-acceptance`: `ethos publish` refuses a release-tag ref while `release_policy_report`
   reports a required gap; the accepted identity binds version, source tree and the attested
   `SHA256SUMS` digest, naming every published wheel and archive, with readers admitting both
   schemas first. After the journey the releasing host installs the release as its global `ethos`,
   and a release operation born in the R2 package (working name `ethos release accept`) checks its
   version and runs `materialize_explicit_release` once; reinstalling the predecessor undoes a bad
   global release.
5. `http-retirement`: the `http:ethos` declaration writer, its assertions and mentions and the
   never-published disk-image writer go, and `SHA256SUMS` joins the attested subjects.
6. `brew-channel`: the GitHub-only tap `HengYangDS/homebrew-ethos` is created with this Change under
   the owner's approval. Its formula takes the `url` and `sha256` of the attested `SHA256SUMS`, has
   no `depends_on`, and installs one launcher that runs the host's Mise by absolute path from a
   neutral ETHOS-owned directory with ETHOS's isolated global file and every Mise verification
   variable cleared, installs the formula's version, requires the locked checksum to equal its
   `SHA256SUMS` line and execs that console; without a Mise it refuses with `next.argv`
   `brew install mise`, and `brew upgrade` or `brew uninstall` moves no repository. The releasing
   agent pushes the rendered formula as a signed commit with no CI credential, B's brew leg runs
   before the tag and from the tap afterwards, and `status` reports two Mise owners as a gap.
7. Migration: each of 11 adopters, the two archived films excluded, pins in one bump lane after R
   (entry and setting, an in-place relock, `mise install --locked`, proof, land, publish,
   `ethos hook install`). GitLab jobs install with `MISE_LOCKED_VERIFY_PROVENANCE=0` and no GitHub
   credential (B.9), jobs that run no ETHOS install named tools only, since archives are 270 to 383
   MB, the proxy retires its CI commit pin, and ETHOS itself pins nothing.

**C.3 Admission, spec deltas and tests.** The selection receipt (C2) has no other owner, since Git
records a departure only once a revert or bump lands and Attestations are immutable while this state
must vanish; hook activation owns it until the accepted pin changes or the lane retires
(PDC:347-357). The identity schema (C4) is an expanded payload of `release:accepted-identity`, read
in both forms until the contract step. Deltas: C1 ADDED "A release installs through one exact GitHub
pin" and MODIFIED the hosted journey requirements; C2 ADDED "Runtime activation follows the accepted
pin forward" and "A lane-bound selection receipt holds a departure" and MODIFIED
`A rollback across a repaired declaration refuses until restored`
(`openspec/specs/runtime-activation/spec.md:412`); C3 MODIFIED the adoption requirements; C4
MODIFIED `Accepted release identity is immutable` (`openspec/specs/distribution/spec.md:369`),
installed supply and `Public channels consume explicitly accepted release artifacts` (`:598`); C5
MODIFIED the declaration requirement; C6 ADDED "Homebrew delegates the global ETHOS to Mise". Tests:
C1's negative cases, relock and stripped table under Mise 2026.10.25 and the hosted journey on
beta.6; C2's fixture adopter covering forward and held-back selection, unattested and checksum-class
locks, no or uninstalled pins, both receipt kinds and closure at lane retirement, which B8 reuses.

**C.4 Boundaries and gaps.** Not in this set: R8(b)'s workflow Change; B's Changes; the fleet
preview and `runtime-by-pin`; a native launcher; an archive formula or Cask; a GitLab mirror or
`gitlab:` pin; the Windows global role (0.3.0). Open for the committee: the selection receipt in
`receipts/` or as an open-predicate Attestation member, and the pin key as a product constant or
derived from the GitHub peer. Unproved: lock format, verification and relocks under Mise 2026.10.25
and 2026.10.23; whether install re-checks the attestation and binds the repository, which C1's
negative cases decide; Linux and Windows installs; Homebrew's discovery of a Mise it does not own
and installed-version rollback; immutable releases.

## Appendix D. Store retention (R7(c))

Source: `build/runtime/work/store-retention/design-draft3.md`, draft 3 with the decision of 05:5x,
which adopts the independent review and fbee0c's review; it cites `bfaa87543`, and the code it cites
here is unchanged at `ff0c09beb`. D.5 adds the resolution's requirements.

**D.1 Conclusion.** Terminal compaction moves a reviewed abandonment's exact per-node manifest to a
content-addressed file bound by digest, kept until the operation is terminal and no unreceipted
request binds it; the request and receipt keep its digest and per-root totals.
`ethos hook retire-records`, run only by the runtime that `runtime/CURRENT` selects, previews lane
retirement units (`terminal` or `superseded`), aged publication requests and four producer kinds of
artifact that no live member, kept record, decoded carrier or accepted-tree token names; it persists
the list before deleting and compares the set root under a non-blocking custody lock before each
unlink batch. On 11-07 a first apply would have freed about 4.69 GiB of 16.64 GiB (estimate).

**D.2 Decisions.** (1) The manifest stays until terminal and while an unreceipted request binds it,
at the cost of a second file per reviewed abandonment. (2) Each artifact kind is its one writer's
exact schema; foreign artifacts and unnamed kinds stay until an owner claims them. (3) Roots are
decoded and over-approximated: tokens in zip, gzip, tar and base64 content count, as do the accepted
tree's, a mistaken match only keeps, and a kept carrier in a format the verb cannot decode refuses
the preview and names its path. (4) Only the selected runtime runs the verb, so defaults, bounds and
the allowlist come from the running package. (5) A write-ahead plan, per-item rechecks and a custody
step per batch replace a whole-plan refusal, which every proof's writes would trip. (6) A read-only
coordinate view classifies units without a receipt as `superseded`, and no inline request is
executed or rewritten. (7) Publication requests retire by age alone, since their one consumer, a
later `publish --receipt` replay, then refuses and points at a fresh publish. (8) No other command
runs the verb, and `ethos status` only reports and suggests it.

**D.3 Design.** Compaction: `_ReviewedContent` (`src/ethos/contracts/retirement.py:54-91`) replaces
`entries` with `manifest` (digest, size and per-root `totals`). The entries go to
`requests/lane-retirement-manifest/<digest>.json` before the request, admission and removal load
them by digest, and a missing or altered manifest (`lane_retirement_manifest_missing`,
`lane_retirement_manifest_mismatch`) leads to a fresh content review. After the terminal receipt the
operation deletes its manifest unless an unreceipted request binds it, reading only manifest
digests; an inline legacy request continues through `fresh_retirement_command` over its coordinate
view. Admission and kinds: the verb refuses with `record_retirement_runtime_unselected` unless the
invoking build is the selected one, and reads `.ethos/rules.toml` from the accepted branch, refusing
an unreadable or malformed floor with `record_retirement_floor_unreadable`. It owns proof-check
documents, merge preimages, native and JavaScript attempt zips, publication requests, lane
retirement units (`terminal`, `superseded`, `receipt-only` or `manifest-only`) and its own plans and
receipts, and reports anything else by path and bytes. A unit without a receipt is `superseded` when
another request for its branch or path has a terminal receipt, no snapshot completed an effect,
worktree, ref and lease are absent at preview and apply, and no root names it. Roots and selection:
a 64-hex token or store path is a root in a live member, in a kept file outside `runtime`,
`packages`, `hooks`, `tool-cache` and `cache` (custody included, the verb's own records excluded),
in a reached item or in the accepted tree, decoded within `retention.decode_depth` and
`retention.decode_bytes`. An owned item qualifies when no file of it is a root and its newest file
is older than its floor: grace for artifacts, record for the rest. Writers: preview and apply refuse
while `proof-slot.lock` is held, the apply holds the slot for the artifact batch, the 7-day grace
floor covers writes outside the slot, and the apply refuses while an open lane or an
older-generation command runs code without the mtime refresh that identical content-addressed writes
now perform. Apply: each invocation takes `<git-common>/ethos/retention.lock` without blocking, and
the preview writes `requests/record-retirement/<digest>.json` (accepted commit, frozen cutoffs, each
item's kind, path, size, mtime and state) before any deletion. Batches are one kind in one directory
under the owner lock, renamed to `.<name>.retiring` and rechecked; outside the custody lock the
apply decodes the custody of newly recorded members, and inside one non-blocking hold
(`src/ethos/adapters/store/custody.py:49-54`) it compares the set root again and unlinks, repeating
a bounded number of times, then deferring. Every set swap takes the custody lock
(`src/ethos/adapters/repo/attestation_set.py:321-327`); an item goes only if unchanged, older than
both cutoffs and no root of a fresh scan; a unit's receipt goes last, and a receipted plan deletes
nothing. Parameters and status: `paradigm.toml` gains the floor rows `grace_seconds` (604,800, bound
7,776,000) and `record_seconds` (1,209,600, bound 31,536,000), which take a higher value without a
reason and treat a lower one as a gap, and the ordinary rows `decode_depth` (6, bound 12),
`decode_bytes` (4 GiB, bound 16 GiB) and `status_bytes` (1 GiB, bound 1 TiB). `status` reports
candidate bytes of the owned kinds and, above `status_bytes`, suggests the preview or a pending
plan's apply; the preview is `local-evidence-write`, and the apply is next-wire-shape's inventory
row 13, `destructive`.

**D.4 Deltas, tests and gaps.** MODIFIED `Linked Work Lane retirement has one exact effect`
(`openspec/specs/repository-governance/spec.md:1680`),
`Destructive Work Lane retirement is a resumable observed transition` (`:2703`),
`Dirty and unbound Work Lane content is retired only through an exact reviewed receipt` (`:5629`),
`Lane retirement exposes one receipt-bound recovery route`
(`openspec/specs/command-plane/spec.md:723`) and `Tunable values are declared parameters`
(`openspec/specs/repository-paradigm/spec.md:834`); ADDED "Store records retire only through an
allowlisted write-ahead plan", whose scenarios cover an encoded mention and an undecodable carrier,
a foreign producer, a lane runtime and a missing mtime refresh, an unreadable floor, a swap between
scan and unlink and a held custody lock, an inline continuation, a superseded unit, a publication
replay and status's next step. Tests add one per ADDED scenario on a fixture store, plus the
receipt, refresh and floor cases, an interrupted apply, a custody-free store and an unselected
runtime's proof holding the slot. Out: custody, runtime generations, packages, hooks and tool
supply, which keep their owners; payload detail; unnamed and foreign kinds; legacy rewrites.
`cache/uv` was already retired by hand on 11-07. Unproved: Windows behavior for an open file under
rename or unlink; bounded-memory decoding of a 4 GiB carrier on the Windows guests; the estimate.

**D.5 Additions from the resolution** (Decision 5, items 1 and 2; not designed in the draft). The
verb is a catalog entry in `ethos.application`, and its destructive apply follows the catalog's
authorization rule once A12 lands. Byte budgets cover its owned kinds, the owner stores that
`proof-output-scratch` writes to and the host store's runtime copies, observed for 48 hours before
the RC, and the explicit, previewed release of an absent consumer joins the verb.

## Appendix E. Lane retirement residue class (R7(b))

Source: `build/runtime/work/store-retention/residue-class-draft.md`, draft 1 with the decision of
11:0x, which adopts the independent review and fbee0c's review; it cites `727ee0579`.

**E.1 Conclusion.** A content review records each ignored root that the artifact topology declares
as residue, and whose native check passes, as one row (path, check, listing digest, files, bytes);
every other node keeps its record. Residue is the root `.venv` (uv's `sync --check`), the root
`node_modules` (npm's hidden lockfile), a `__pycache__` of `.pyc` files beside their sources and
each declared tool directory under `build/runtime/tool-cache`; `build/evidence`, `build/ethos`,
`build/runtime/work` and `build/artifacts` keep the full review. Rows would have replaced up to
86.5% of the 1,001,177 records reviewed since 11-02, a ceiling before the amendments narrow the
class. The Change lands after D.

**E.2 Decisions**, as amended. (1) Rows only for declared, ignored, checked roots;
`build/runtime/work` stays undeclared despite its `runtime_cache` label, because agents author
there. (2) The producer's own check proves that a root matches its lock: uv reports no change for
`.venv`, and for `node_modules` npm's hidden lockfile equals the lock and no package is undeclared.
(3) The row digest covers each node's identity (device, inode, mode, owner, size, mtime, ctime,
links) and link target, with no file hash. (4) An interrupted removal is drift and selects a fresh
review; it cannot resume under the same receipt, and the recovery scenario says so. (5) Unique
content stays reviewed: a `.pyc` is residue only beside its own source; each tool directory is
declared on its own, and Hypothesis's example databases keep per-node review, since they hold
failing examples that no command reproduces; a `.venv` or `node_modules` root keeps per-node review
when any of its files changed after the install that its check vouches for. This settles open
question 4 against fbee0c's answer, "the declaration alone". (6) The Change's first task runs the
exact `uv sync --check` on real lane `.venv`s, which hold the project as an editable install. If it
cannot pass with the gate's flags, the design uses the native selection that includes the project or
narrows `.venv` rows to what passes, and the measured share replaces the 86.5% ceiling. (7) Windows
keeps per-node review, since Python's `st_ctime` there is the creation time. (8) When only residue
remains, `retire landed` records the checked rows and removes them, so disposal rests on the
declared check and leaves an audit trail; unique content keeps the review route. (9) One
densification serves the queued Changes' tests; if the measured need exceeds the freed space, one
5,000 step is taken with that evidence. (10) Keep-out: an adopter's declared commands get
`UV_PROJECT_ENVIRONMENT` and `PYTHONPYCACHEPREFIX` in the attempt's scratch, with per-gate
exceptions for `ty` and the Node supply; Family 3 names this `proof-output-scratch`.

**E.3 Design.** `src/ethos/contracts/artifacts/topology.toml` gains `[[residue_root]]`: `.venv`
(`uv-lock`) and `node_modules` (`npm-lock`) by path, each declared tool directory (`cache-home`) and
`__pycache__` (`bytecode`) by name; the declaration model refuses a row inside a promotion-allowed
home, so `build/evidence` can never be one. Before its first snapshot, `reviewed_content` runs
`git ls-files -z -oi --exclude-standard --directory`; a candidate qualifies when it or an ancestor
is a listed directory, it is a real directory outside a promotion-allowed home and any other row,
and its check passes: `uv-lock` runs the exact `uv sync --check` with the default selection on
`UV_PROJECT_ENVIRONMENT=<lane>/.venv`, `npm-lock` one public check built from the node supply's lock
comparison, and `bytecode` admits regular `*.pyc` files beside their sources. The snapshot walks
each root with its owner, filesystem and nested-repository refusals and puts its nodes, unhashed,
into the listing that the row's SHA-256 digests, and a second snapshot must give the same rows.
`_ReviewedContent` gains `residue`, a tuple of `{path, check, digest, files, bytes}` rows, validated
as normalized, non-nested paths under `entries` with no entry at or under a row and bound by the
request digest. Rows stay inline beside D's `manifest` and `totals`, which count only entries, and
end with their request and receipt under `retire-records`; both Changes edit `_ReviewedContent`,
`content.py` and one spec line, so this one lands second. The apply re-walks each present row root
and requires its digest, an absent root counting as removed, and unlinks deepest first, each node
rechecked, without running uv or npm.

**E.4 Admission, deltas, tests and gaps.** Under PDC:347-357 the row is a cheaper form of today's
per-node entries for the same invariant, that a lane retirement removes only what its review bound,
and no new entity; per-node review of residue costs most records and about 458 MB of hashing per
review. MODIFIED `Linked Work Lane retirement has one exact effect`
(`openspec/specs/repository-governance/spec.md:1680`), with an ADDED scenario "Reproducible residue
is reviewed as one row per root";
`Dirty and unbound Work Lane content is retired only through an exact reviewed receipt` (`:5629`);
and `Generated artifact topology binds the root project environment` (`:5312`), where the root
`.venv` is a row only while uv reports no change. Tests: an ignored `.pyc` is one row and its
replacement drifts; a write into a row root after observation removes nothing; a new
`test_residue.py` covers clean and changed `.venv` results, equal and unequal hidden lockfiles and
an undeclared package, a `.pyc` without its source, the kept `build/` homes, a tracked file under
the tool cache, Hypothesis databases, a `.venv` holding `__pycache__` and a partly removed root; a
row in a promotion-allowed home refuses the declaration. Out: tracked nodes, D's backlog, Trash
disposal. Unproved: that the exact uv check accepts a lane `.venv` offline and writes nothing; which
producer left an adopter's `.venv`; that uv's hard links on Linux drift a row's ctime, which costs a
fresh review and never a loss; Windows `st_ctime` behavior on Python 3.14.

## Appendix F. Peer identity records (R8(e))

Source: `build/runtime/work/peer-neutral-artifacts/peer-identity-records-draft5.md`, draft 5 with
the decision of 05:4x and the amendment of 06:0x, which adopt the independent review and the reviews
of AIGW and fbee0c; it cites `bfaa87543`, and the code it cites here is unchanged at `ff0c09beb`.
Labels: H1 host, P1 and P2 ports, F1 namespace path, G group, I1 project ID.

**F.1 Conclusion.** The Change keeps the owner's peer identity out of what the owner's repositories
publish, through one shared grammar that G consumes. What the peer already advertises counts as
disclosed: the push check reads only the commits a push adds beyond every tip the peer advertises,
and it is `unknown` when that cannot be read. A backstop-only check in a commit-range job is inert
without GitLab variables and blocks only on a fed literal under `required`. The keyless verifier
needs no identity, and nothing here makes a record immutable.

**F.2 Shared grammar**, one module (proposed `src/ethos/repository/paradigm/peer_identity.py`) that
the push check, the verifier, the verb and G import. (1) Kinds, disjoint and decided by neighbours
and the declared port alone: `url` (after `//`), `scp` (`[user@]host:` with no declared port after
the colon), `authority` (`[user@]host:<declared port>`, consuming the port) and bare `host` (no `//`
or `@` before, no `:` after); an unclassified occurrence blocks `--apply` as `manual`. (2) The
marker `<hex32>.<hex32>.private-peer.invalid` is a valid host made of one HMAC-SHA-256 over a
NUL-joined UTF-8 pre-image: `ethos.private-peer.v1`, `kind` (`prefix`, `host` or `path`), the
lowercased host, the port or empty, and the lowercased path without edge `/`, `.git`, `?` or `#`;
scheme and userinfo are never hashed, and the `scp` and `url` markers of the same parts differ. (3)
The key is 64 lowercase hex characters, at most one trailing newline, never all zero
(`redaction_key_invalid`). (4) An I1 value is replaced within 100000000 to 999999999 and a
standalone port within 1024 to 65535 by `n = lo + (u64_be(HMAC(key, m)[:8]) mod (hi - lo + 1))`,
where `m` is `"ethos.private-peer.v1" NUL role NUL dec(v) NUL dec(c)`, raising `c` from 0 until `n`
differs from the original, every other replacement and every fed value and is absent from the domain
(the tracked tree at `--base`, or the rebuild's originals); `n` is never 0, and more than 4,096
probes refuses. (5) Closed contexts, counted only with a recorded, digit-bounded literal: for I1,
`projects/<I1>`, `projects%2F<I1>`, `CI_PROJECT_ID[=:] <I1>`, `project <I1>`, `ID <I1>`, the
`--project-id` and cache path forms, `IDs <public> and <I1>`, `project-<I1>`,
`.<name>-mise-mirror-<I1>`, `projectID = "<I1>"` and `project_id[=:] <I1>`; for ports, `port <P>`,
`port=<P>`, `port: <P>`, `"port": <P>`, `<word>_port[=:] <P>`, `--port[= ]<P>` and `-p <P>`, never
22, 80 or 443. (6) Markers and pre-images map one to one, a marker already in the originals is
admitted only when the key shows the same pre-image, and keyless checks treat it as opaque; host
boundaries are the paradigm pattern's (`src/ethos/contracts/paradigm/paradigm.toml:13`).

**F.3 Span.** For `url`, `authority` and bare `host`, the span is the host, an optional `:port` and
whole leading `/segment`s, a trailing `.git` consumed with the last segment, while userinfo and the
rest of the line stay byte-identical. For `scp` the span is the host alone, and the path after the
colon is a standalone `path` span, so `git@<H1>:<F1>` becomes `git@<marker>:<marker>`; a span may
also start at a module path's first element. A digit run in a closed context is replaced number for
number. The verb and the rebuild write through `replacement_spans(line, fed)`; the verifier needs no
feed and accepts the same shapes by alignment.

**F.4 Push-time check.** It runs in `push_admission_report`
(`src/ethos/adapters/admission/publication.py:343`), the one owner that readiness, in-process
admission and the hook call, inside the measured deadline, with one range for every kind of push. A
push reads `<pushed> --not <every tip the peer advertises>` from one bounded `ls-remote` per peer,
skipping tips absent locally and excluding annotated tags through their peeled commits; a pushed tag
adds its message. An unreadable advertisement is `unknown` and under `required` refuses with
`peer_identity_range_unknown:<remote>`; the check never scans the whole history.
`peer_identity.mode` is read at the commit whose policy push admission already trusts (a new ref's
creation baseline, the accepted head on accepted delivery) and at an advertised tip of the target
ref, never in the working tree; under `required`, an unreadable peer remote refuses with
`peer_identity_feed_unreadable:<remote>`. The feed is local state only: remote URLs and
`forgeRepository` give H1, P1, P2 and F1, the multi-valued `remote.<name>.forgeProjectId` gives I1
and former IDs, and `remote.<name>.forgeFormer` holds former hosts, full paths and ports. A peer is
protected when H1 is private-class or the local `remote.<name>.forgePrivate` opts it in. Added lines
and messages refuse a fed host, a fed full path (a one-segment namespace never counts alone, since G
alone is a historic package identifier), `:<P>` after any host, and a closed context with a fed
value, former values included, as `peer_identity_literal:<form>:<n>:<m>:<line>`, which never repeats
a value. The adopter's backstop job runs `hook commit-range --check peer-identity` with its own
exit: no signature or commit policy, a missing baseline only as the advisory
`peer_identity_backstop_baseline_missing`, and exit 1 only on a fed literal under `required`. It
reads `CI_SERVER_HOST`, `CI_SERVER_PORT`, `CI_PROJECT_PATH` and `CI_PROJECT_ID`, is inert without
them, and runs on pushes to `dev`, `main` and `proposal/*` and on merge requests. Stated limits:
`git push --no-verify`, a hookless clone, a raw new-branch push, a deleted and re-added file,
another spelling of H1, a port in free prose, headers, path names, binary and UTF-16 files, and the
backstop's missing SSH port.

**F.5 Record roots and cutover.** `RepositoryProfileDeclaration`
(`src/ethos/repository/profile.py:226`) gains `record_roots`, directories only, and
`peer_identity.mode`, `disabled` by default or `required`; effective roots are the paradigm's
`immutable_roots` plus `record_roots`, with no added immutability, and a protected peer under
`disabled` and the readiness count are `status` advisories. An adopter turns `required` on in the
lane that declares its roots once its readiness count, the fed literals outside the effective roots,
is 0; two adopters also need `peer-neutral-outputs`, which has no design yet (owner 97f828). Mode,
roots and wib's `[artifacts]` repair to `record_roots = ["evidence/"]` move in one profile-format
lane per adopter, whose predecessor reports `repository_profile_invalid`, and the rollback preflight
reads the other runtime's result through `expand_result`. The backstop job goes through each
adopter's CI declaration owner.

**F.6 Keyless verifier.** It runs in `_validate_commit_revisions`
(`src/ethos/adapters/repo/commit/integration.py:202`) on changed lines under an effective root that
introduce a marker, with no identity input, so hosted CI runs it unchanged; roots per revision are
the union declared at the commit, the incumbent baseline and the proposed head. Each marker line
pairs with the removed line it reproduces: split at its markers and at closed-context digit runs,
its literal pieces must appear in order in the removed line, each gap one admitted span and each
differing digit run the keyed replacement. An unpaired marker line refuses with
`record_marker_unpaired`, a malformed marker with `record_marker_malformed`, and one equal to the
plain SHA-256 or empty-key HMAC of its pre-image with `record_marker_unkeyed`; merges are judged by
`--cc`.

**F.7 The verb.** `ethos lane redact private-addresses` is a tracked write under prewrite and the
Lease. Its keyless default preview lists file, line, form and the readiness count, never a value.
`--apply --key-stdin --authorize --expect-head <oid>` writes markers and numbers in the effective
roots under an exact-head compare, in the working tree only, and an unfed path after a replaced host
is `manual` and blocks it. `--verify --key-stdin --base <rev> --head <rev>` re-derives every marker
and number from the pre-redaction revision and on a pass records an Attestation
`redaction:private-peer` (base, head, roots, count and the key generation
`hex(HMAC(key, "ethos.redaction.generation.v1"))[:16]`) without `--authorize`. A redacted file whose
digest a record in the same commit holds gets that digest rewritten, and a key of another generation
refuses unless `--rotate` is given.

**F.8 Deltas, tests and gaps.** `repository-paradigm`: MODIFIED
`Tracked content and commit and tag messages carry no private-class network address`
(`openspec/specs/repository-paradigm/spec.md:887`), whose scans read the commits a push adds beyond
every advertised tip, and ADDED the grammar, span, numbers, binding and verifier.
`repository-governance`: ADDED the push-time check under the push budget and MODIFIED the profile
and `status` advisory requirements. `command-plane`: ADDED the verb. `runtime-activation`: MODIFIED
for the rollback preflight. Tests cover the grammar and replacement rules, the verb's output through
the feed-free verifier, push ranges and an unreadable advertisement, the backstop's exits, verifier
pairing with a replaced port, and rotation. Out: record-root immutability, history rewriting (G),
key creation and Keychain access, and the changelog link format. Unproved: no test, hook or forge
call ran.

## Appendix G. History rebuild map (R8(e))

Source: `build/runtime/work/tag-replacement/history-rebuild-map-draft8.md`, draft 8 with the
decision of 03:5x, which adopts the independent review and AIGW's review; it cites `bfaa87543`, and
the code it cites here is unchanged at `ff0c09beb`. Labels: H1 host, P1 and P2 ports, G group, F1 to
F4 namespaces, I1 and I2 project IDs.

**G.1 Conclusion.** A rebuild keeps its originals in a local side bare repository that owns its
objects and is never a remote. A rebuild record and its attempt, result and applied ref-update
records share one lifetime key and end only on an owner purge, so the owner's reflog expiry and
`gc --prune=now` break no reader. Readers run in the main repository under its governed trust anchor
and use the side store only as a checked, read-only alternate. Every namespace of at least two
segments is a `forge-path` entry, readiness blocks on any protected path that stays untied, and
`--release` drops only the tag-only replacement refs. The grammar and marker are F's. For R8(e),
ETHOS runs the readiness scan over its own declared refs and records the disposition (Family 6).

**G.2 Decisions.** (1) Every rebuild record takes the key `rebuild:<id>` from the `id` that
`history.transform` carries, so the lifetime classifier reads no object; "one record per `id`"
counts results only, and all records end only on a recorded owner purge. An absent or emptied side
repository is unobservable: readers that need originals refuse, and nothing ends. (2)
`<common>/ethos/rebuild/<id>/originals.git` owns all its objects, without alternates either way, and
is created after the key check with `gc.auto=0`, no hooks and no remote; readers attach it per
command as a read-only `GIT_ALTERNATE_OBJECT_DIRECTORIES` entry and refuse if it has gained an
`objects/info/alternates` file. (3) One span entry per discovered identity span (a host, an optional
port, at most one full path), each with its marker and witness; `url`, `scp` and bare `host` each
have their own match context (F.2, item 1), and one left-to-right scan takes the longest bounded
entry of the applicable kind at each position without rescanning its output. (4) Parts are typed and
peer-tied: `host`, declared ports, `forge-path` (two or more segments, counted after decoding) and
`project-id`. A namespace is tied by its leading-prefix occurrences after a declared host, port or
scp colon, or by a merge-request citation's full path; its lone occurrences take its marker, and it
refuses inside the public peer's path. The one-segment group G stays, and no free strings exist. (5)
The public path is that of the URL `forge_web_repository` returns for the declared
public-distribution peer, compared with the record's `key.account`, case-insensitively on GitHub;
review of `key.account` binds it, and a mismatch or an unresolvable peer refuses. (6) Markers and ID
replacements are distinct and absent from every original, the record blob binds each declared ref
with its disposition and old value, and an undeclared span, port, path or context, or an untied
protected path, refuses. Authorization is the Change-local `rebuild.toml`, bound by `old`, path and
blob ID, whose expiry gates only a new apply.

**G.3 Record.** `rebuild.toml` sits in the authorizing Change's directory and lands through a normal
signed landing, so both peers carry it before the apply. It holds `version`, `id`, `owner`,
`reason`, `expires`, `base`, `key` (service and account), `[refs]` (every ref that reaches an
affected commit, with disposition `rebuild`, `retag` or `retire` and its old value) and
`[transform]`: trailers to remove; hosts, paths and ports by `hmac-sha256` digest with a signed
witness (commit, path, offset, length); spans; IDs with their declared public contexts; and `retain`
prefixes. No part is in clear, and a test runs the private-class scanner over the record. `history`
keeps `transform` (`version`, `path`, `blob`, `id`), `refs`, `reason`, `backup` and
`affected_count`, and the result adds `replacements`. `old` is the accepted head at apply, and
`base..old` touches only the authorizing Change; the paradigm's `[openspec]` table declares the file
as the one Change-local record ETHOS reads. A record's blob must be the one at the path in `old` and
in its rebuilt image, records name originals by signed commit and tag IDs, and trailer removal keeps
today's `Co-authored-by:` rule (`src/ethos/adapters/repo/commit/history.py:77-91`).

**G.4 Substitution and discovery.** For Go, each identical string maps to one replacement in every
file of a commit, so `go.mod`, imports and `-X` link flags agree. A `project-id` is digits only,
tied by one `CI_PROJECT_ID=<ID>` occurrence and replaced only inside a declared context. Governance
TOML, YAML and JSON parse before and after to the same keys and value types, a binary blob that
holds a declared item refuses, and at `old` an item may remain only under an immutable root.
Readiness, without `--apply`, walks the originals of every declared ref once and reports by count
and fixed gap name, never by value, every distinct span, every path after a host or scp colon, every
module path's first element, every encoded path, every merge-request citation's path and every ID
context hit.

**G.5 Apply.** The apply, `ethos lane repair-signature --rebuild <path> --backup <bundle>` with
`--key-stdin --apply --authorize --expect-head <old>`, (1) refuses unless the binding holds, the
expiry has not passed (a recorded attempt still recovers), every declared ref holds its own value on
both peers and the bundle lists every declared old value, and refuses any `work/` or `proposal/`
ref, a non-empty `refs/ethos/*` on a peer and a dirty worktree on a declared branch; (2) after the
key check, creates the side repository, fetches the declared refs and every release-named commit and
runs `fsck`; (3) checks each digest against its witness under the key and records
`marker_digests = "verified"`, bound to the digests, the key generation and the blob; (4) computes
the affected set, the commits whose tree or message holds a declared item and their descendants; (5)
writes signed commits in topological order, reusing signed payloads on recovery, then checks that
nothing reachable from a rebuilt tip or a retagged tag holds a declared item or a private-address
match; (6) runs one `commit.identity-replace` plan with each ref's own old and new value. Open
`work/` lanes land and retire first.

**G.6 Verification and readers.** One owner in `commit/history.py` verifies a transform record from
the whole `history` mapping: the blob parses and the ref set is the blob's, the walk yields one
bijection of the recorded size, every changed object is recomputed from its original by the declared
entries alone, every rebuilt commit is trusted, and the attempt holds `marker_digests = "verified"`.
Each reader adds one relation: the hook admits only the result plan's updates; historical source
admits the record's refs; retag maps the tag's original target; release and publication of a
re-created tag require the trusted original tag object and verify its proof against the original
commit's tree; publication, conservation and archive provenance map across the rebuild edge.

**G.7 Refs, leaks and cost.** `rebuild` moves dev, main and candidate/dev; `retag` re-creates
affected annotated tags through `ethos land --retag` with the message transformed; `retire` removes
the `native-inputs-<carrier>` tags through `published-tag-replacement`;
`refs/ethos/attestations-set` is never rewritten or published.
`refs/ethos/rebuild/<id>/rebuilt/<ref>` keeps each tag-only replacement until both peers'
publication receipts show every rebuilt branch and retagged tag and no retired tag, then `--release`
deletes them in one recorded plan. Reports say "originals held locally", never "purged"; failure
reports drop `stdout` and `stderr`; no Git argument carries a literal; a verdict cache keyed by
record digest, ref pairs, trust anchor and runtime covers the roughly 200 hook updates of one
adopter's apply.

**G.8 Deltas, tests and gaps.** `repository-governance`: ADDED the versioned record transform, its
authorization by a declared Change record, typed span entries, discovered completeness, keyless
verification and the side repository; MODIFIED
`Attestation lifetimes end with the transition that consumes them`
(`openspec/specs/repository-governance/spec.md:4203`), `Bounded accepted signature replacement`
(`:3287`), `Publication composes historical repair with forward integration` (`:3581`) and
`A repaired release tag is re-created on its replacement commit` (`:6215`). `command-plane`:
MODIFIED `Accepted signature repair command` (`openspec/specs/command-plane/spec.md:960`) with
`--rebuild` and `--release`. `published-tag-replacement` owns two undesigned requirements: a retag
push starts no CI, which the adopter confirms by two bounded, prompt-free reads. The record drafted
as DR-0019 takes a free number (Decision 5). Tests cover the transform kinds, a Go fixture's rebuilt
version, every refusal, a refused hooked mirror push, survival of `gc --prune=now` and reflog
expiry, and a fixture published to two bare peers. Out: tag publication, the owner purge,
identity-bearing release assets, which the owner deletes outside ETHOS, and copies outside the
rebuilt refs.

## Appendix H. Defect register mapping

Source: `build/runtime/work/beta2/essential-fixes-20261105.md`, 30 rows written from 11-05 to 11-07,
mapped at `ff0c09beb`. A closing commit is the archive commit of the closing Change, or the fix
commit that the register or the resolution names, and each is an ancestor of `ff0c09beb`. Where no
resolution item, draft or register row names an owner, the assignment is this design's.

Closed on dev:

- Row 1 (results lose their causes): `3251dc200`, `cause-preserving-results`.
- Row 4 (undeclared release contents): `b44eab5a1`, `release-inventory`, and `416163a20`,
  `release-binary-scan`; the binary subject in dependency acceptance that the scan deferred is 0.3.0
  (owner 97f828).
- Row 8 (a carrier outlives its content): `da7996b22`, `dead-carrier-closure`.
- Row 9 (tests failing at 03:35): `32d94043c`, `gate-scratch-access-times`, pending R11's proof
  across 03:35; the `flaky` outcome class is 0.3.0.
- Rows 11 and 18 (a lock move without its supply image): `424c291b3`, `supply-image-currency`.
- Row 14 (the closed verdict set note): `f26eb9e4e`, `beta-3-release`.
- Row 15 (lanes based before a rule change): `e979102f9`, `integration-gap-transport`; `fast-tier`
  makes the pre-proof architecture run native.
- Row 16 (the quality fixture lock): `c4279fd32`, `quality-fixture-lock`.
- Rows 17 and 25 (audit network resets and misreport): `e5bcda62c`, `audit-reset-resilience`.
- Row 19 (latent static defects): `4ca9b9eb1`, `proof-readiness`, and `a0cbdcf33`,
  `proof-readiness-full-plan`.
- Row 20 (GitLab artifacts over the limit): `a33941a54`, `gitlab-evidence-artifacts`, and
  `3ac186f03`, `gitlab-archive-contract`.
- Row 21 (release jobs first run at tag time): `2b279b285`, `release-runtime-syft`, and `6b04be60d`;
  the class fix is B6.
- Row 22 (the Windows inventory check): `68e612b34` and `32a7ccc99`, `release-node-declaration`; the
  upstream Syft issue is its maintainers'.
- Row 23 (a failed optional leg vanishes): `89473e4a1`, `release-declared-legs`.
- Row 24 (the scan first ran at tag time): `6b04be60d`, `release-step-coverage`; its beta.3 dispatch
  cannot be read offline (unverified).
- Row 28 (operations that drop commits): `2622cd79f`, `housekeeping-reachability`, and `c712216d9`,
  `next-wire-shape`.
- Row 29 (readers that miss the result bound): `0844b353e`, `bounded-reader-guard`, after
  `e542a8909` and `0f71e0cc0`.

Open, owned by an RC Change:

- Row 3 (the journey is not hermetic): B2.
- Rows 5 and 13 (host contention; GitLab deadlines under load): `host-reservation` (Family 4), with
  the guests' host owners, AIGW and fbee0c, after the host queue of `3d73a3fdd`; meanwhile a
  guest-job timeout is retried once and counts as no product evidence.
- Row 7 (a one-line test gap found late): `fast-tier` (Family 4).
- Row 12 (evidence refs in history-wide scans): `evidence-ref-scan-scope` (Family 6).
- Row 26 (cancellation refused while the group leader exits): R11's diagnoses (owner 97f828); a
  recurrence opens its own Change.
- Row 27 (lane retirement keeps every reviewed path): D, E and `proof-output-scratch` (Family 3).
- The items deferred under rows 21 to 24: the rehearsal is B6 and B7; the failed leg's record joins
  B6's receipt; the adopter platform check moves to C1's in-place relock (inference); the Windows
  journey leg is 0.3.0 (owner decision 4); the Mise `credential_command` warning joins B2's fresh
  HOME (inference).

Open, owned outside the RC:

- Row 2 (identity coupled to qualification): `channels-decision` records the decision, and the
  channel model is 0.3.0.
- Row 6 (agent kits share the product's work namespace): A17 retires the kits; the product's
  declaration of its own work directories is 0.3.0 (owner 97f828).
- Row 30 (an unbound successor's preview reads as "nothing to do"): the next release entry states
  the preview method; naming both the invoked and the answering build is 0.3.0 (owner 97f828).
- Row 13's npm advisories: no action; the dependency policy blocks once a fixed bundle ships.

Withdrawn: row 10, the fix-age window, by the owner on 11-05 at 14:0x.
