---
subject: ethos:research-change-surfaces-peer-mechanisms-reading
role: research
state: active
relations:
  part_of: README.md
---

# Peer Mechanisms: What Is Worth Taking

Research date 2026-11-18. Review by 2027-05-18. This page is a reading, not a finding: it ranks
what the [study](peer-mechanisms.md) reports. It decides nothing and schedules nothing.

## The reading in one paragraph

ETHOS is ahead of every source read on the effect: what may be written, how it lands, what is
recorded, how it is recovered. No source lands by compare-and-swap, signs its evidence into Git,
or keeps its proof planes apart. The sources are ahead at the two ends that the effect does not
reach. Before the work: is the intent settled, by someone other than the author, before the code
that claims it; and what did the change say it would touch. After the work: does each thing the
change promised have evidence of its own; and who, other than the author, approved. In ETHOS's
own terms, of the four roles (legislator, author, verifier, approver) the mechanism serves the
author and the verifier. The approver's act is left to the forge's review of a `proposal/*`
object, a maintainer may land without it, and ETHOS's evidence records nothing of it. The
acceptance that a proof binds is compiled from a Change that the same author wrote in the same
lane. A proof therefore shows that what landed is what the Change says and that the gates
passed. It does not show that the Change says what was asked, or that anyone else agreed.
Items 1 to 3, 5 to 7, 10, 12 and 14 below each close a part of that gap. The others serve
parts of the law that ETHOS's own plan lists as open: waivers (4), an agent's budgets (8, 11),
the clock by which a rule arms (9), the forge's own settings (13), and what a reader who was
blocked is told (15).

Each item gives the evidence, what ETHOS has, what taking it would mean, and what could show
that it is not worth taking. "ETHOS today" is read from the documents the study lists and from
eight accepted requirements; most of the accepted specifications and all of the source were not
read, so a "nothing" below means that what was read names nothing.

## Ranked

### 1. An approval is a recorded act by someone who wrote none of the change

- **Evidence.** ControlCoding refuses a review written by the implementer of the change under
  review. CoaseEdge
  takes approval only from an allowed reviewer's review whose `commit_id` is the live head, and
  refuses a waiver file that carries its own approval. Spec Kit has marks only the reviewer may
  set. agent-orchestrator binds a reviewer to exact object ids and gives it no way to write.
  loop-engineering's design checklist has the line 'Implementer **cannot** mark its own work
  "done"'. Ten sources separate the
  two roles in some form.
- **ETHOS today.** Every commit is signed and a policy may name exact authors and committers.
  The roles are named, and "keeping author and approver apart is a target". Authority ranks
  "truth sources rather than act as an identity or permission engine", so an approval can only
  be evidence. 0.2.0 has "no scope, expiry, revocation or approver key for an agent's remote
  writes" (DR-0026, Waiver 2); that delegation moves to 0.3.0. Review runs on the forge, over
  a `proposal/*` object; a maintainer "may accept the reviewed object by exact CAS". ETHOS
  records no approval of a change.
- **Taking it.** Product code, after 0.2.0: an Attestation predicate for a review (exact commit,
  tree and Commitment; a signer who authored no commit of the range), which a repository may
  require before `land`. It belongs beside 0.3.0's delegation, which brings the approver key.
  ETHOS already has what the peers lack, authenticated identity.
- **Not worth taking if** the fleet has one signing identity for every actor. Then the check
  compares a key with itself. Count the distinct signers of the last hundred commits in each
  governed repository first.

### 2. The intent is accepted before the code that claims it

- **Evidence.** Eight sources (first pattern of the study). The closest are OpenSpec's own
  contribution rule (a proposal, then its implementation) and intent-driven-template, which is
  built on OpenSpec: "Every OpenSpec state change must cross `main` before the next lifecycle
  phase depends on it." Its zone rule keeps specification and code out of one commit.
- **ETHOS today.** By what was read, a Change and its code may be written in one lane and land
  together. A `proposal/*` ref can show an object for review; nothing makes an accepted
  proposal a condition of writing code.
- **Taking it.** In two steps. A rule, decidable at commit admission: a commit changes a
  Change's proposal and specs, or it changes code, not both (tasks excepted). Then an option:
  for a repository or a zone, `lane prewrite` admits paths outside `openspec/` only while the
  Change's proposal and specs are on the accepted ref or carry the approval of item 1.
- **Not worth taking if** most Changes change their own specs after their first code commit
  for good reason: the gate would then mostly produce second approvals. History can answer:
  count them over the archived Changes. Also if the owner's direction on iteration speed
  outweighs it; the first step costs little either way.

### 3. Each thing a Change promises has evidence of its own

- **Evidence.** qualitylayer: "A point passes only with evidence", shown beside the point.
  ProductSpec gives each criterion an identity and each run a status for each. In
  intent-driven-template the scenarios are the tests. Kiro links a property to its requirement
  and task. gsd-core writes the reading before and the reading expected into the criterion, and
  proves that a guarding test fails first. Spec Kit, cc-sdd and OpenSpec's verify check that no
  requirement is left without a task.
- **ETHOS today.** A proof binds gates to a head. Nothing ties a requirement or a scenario to a
  task, a test or an Attestation. The terminal plan lists "Compile requirement coverage into
  exact proof obligations" as open.
- **Taking it.** In order of cost: a decidable check that every requirement of a Change is
  named by a task (from OpenSpec's own JSON); a task form that names a command, its reading
  before and its reading expected; a reader's projection that lists each scenario with the
  evidence that covers it, and "none" where there is none; last, and optional for a repository,
  scenarios that run.
- **Not worth taking if** the mapping costs more than it finds. Try it by hand on one archived
  Change: how many scenarios can be tied to a test in an hour, and did any turn out uncovered.

### 4. A waiver that cannot approve itself and ends with what it covers

- **Evidence.** CoaseEdge's source (`src/waiver.mjs`): a closed set of six fields, none for
  approval; a binding to the base and to the fingerprint of the diff; an expiry; a list of the
  rules that may be waived at all, the rest marked `waivable: false`. qualitylayer re-opens an
  acknowledged finding when its function, the analyzer's configuration or its metric changes.
  gsd-core's record of six failed designs ends in one sentence: the data "has PR lifetime and is
  stored in permanent, shared, merge-path state". Evagix: a waiver stays visible and is never
  evidence. Spec Kit asks for the simpler alternative and why it was rejected.
- **ETHOS today.** Break-glass is exact, reasoned and receipted. A waiver, exception or policy
  change "still becomes a bounded Commitment/Change". Release waivers are owner decisions in a
  Decision Record. "bounded waivers through one resolver" is an open dependency.
- **Taking it.** A document now, as the resolver's design input: the five properties above.
  Code when the resolver is built. ETHOS's rule that a waiver is itself a Change already gives
  it an author, a review and a history; the peers add what it must be bound to and when it ends.
- **Not worth taking if** ETHOS decides that no rule is waivable below the release gate
  ("A repository cannot declare an exception", DR-0012). Then only the form of a release
  waiver gains, by the rejected-alternative column.

### 5. A Change declares its boundary, and the diff is compared with it afterwards

- **Evidence.** CoaseEdge's task contract and RG009: kinds of change that a task may make,
  mapped from paths by the repository, with "Adding a category ... is a human authorization
  change". cc-sdd's `Out of Boundary`. ProductSpec's `in`, `out`, `cut`. Spec Kit's logged
  deviations. elephant-goldfish-model's declared track. OpenSpec's own `affected_areas`, which
  nothing reads.
- **ETHOS today.** Nothing for one Change, on purpose. The accepted requirement attributes
  changed paths to the one active Change as "a fact, not an authored scope or permission
  carrier", and lists `scope.toml` among the things that authorize no write: ETHOS has had an
  authored scope and removed it.
- **Taking it.** Without touching admission: the repository maps paths to kinds of change; a
  Change names the kinds it means to make (in OpenSpec's metadata, where `affected_areas` and
  `x-` keys already exist); `ethos plan --changed` reports the kinds the diff touched and those
  not declared; an excess is a question to a person, not a refusal. It is evidence about the
  intent, never permission.
- **Not worth taking if** the owner reads even a comparison after the fact as the authored
  scope that the requirement excludes; this is the item most likely to be refused on principle.
  Or if ETHOS's Changes span most kinds as a rule: classify the last thirty archived Changes by
  hand first.

### 6. Declared zones raise the proof and name who must approve

- **Evidence.** CoaseEdge's risk zones raise the verification level and never lower it.
  maintainer-contracts raises what the description must show for the paths touched.
  se-codeowners routes review from surfaces and roles. loop-engineering and qualitylayer gate
  authentication, payments and agent controls. None infers risk from code.
- **ETHOS today.** Gates are selected by path. Independent verification is set for a whole
  repository. No declaration ties a path to a role or to a deeper proof.
- **Taking it.** Product code: a declaration in the repository's bindings (paths, overseeing
  role, minimum proof set, whether item 1's approval is required), read by the same resolver
  that selects gates; a `CODEOWNERS` projection for both forges from the same declaration.
- **Not worth taking if** the governed repositories are small and of one owner, so that every
  path has the same risk and the same approver.

### 7. A review by readers who never saw the conversation, with every finding disposed of

- **Evidence.** elephant-goldfish-model (20,895 stars) is built on it. BMAD's triage: verify
  the consequence at the place named, record every dismissal, never defer what the change
  caused, and take findings on a third pass as a sign of a fault upstream. gsd-core's ledger
  cites each finding by `L##@{sha}`, appended and never edited.
- **ETHOS today.** The acceptance asks that "A different Agent must resume from repository
  evidence without a retelling". No step tests it, and no document says how a review is run or
  where a finding's disposition goes.
- **Taking it.** A skill and a short guide, no kernel code: a fresh-context read of a Change's
  proposal, specs and design before a person reads them; the triage rules; a dispositions
  section in the Change that cites the reviewed commit.
- **Not worth taking if** such reviews have low precision here. If a precision figure exists
  for the agent reviews already run in this project, it settles the question; this study did
  not look for one.

### 8. Budgets for an agent, with a typed stop and one question at the end

- **Evidence.** BMAD stops at "review repair loop exceeded 5 iterations (non-convergence)".
  qualitylayer allows two fix rounds, then asks one question with three answers.
  loop-engineering escalates on the third failed attempt and ties each level of delegation to
  a record of the verifier being right. agents-best-practices lists the kinds: steps, time,
  tokens, cost, calls.
- **ETHOS today.** The agent budgets are planned as part of an acceptance and not built. The
  typed question exists (`await-user`).
- **Taking it.** Design input for that work: budgets counted on what ETHOS can observe
  (prewrite refusals, proof attempts, commits in a lane), non-convergence as a named stop, and
  the three answers (change the acceptance, one more round, stop).
- **Not worth taking if** the loop that needs the bound runs wholly inside the agent's host,
  where ETHOS sees nothing. Then it belongs in a skill, not in ETHOS.

### 9. A baseline that a change may shrink and never grow

- **Evidence.** CoaseEdge's architecture baseline is byte-stable, and removing it in the
  evaluated diff "fails closed". Its task failure baseline separates failures that predate the
  task. gsd-core pins the size of every instruction file. qualitylayer marks a finding
  "Previously seen".
- **ETHOS today.** A rule "reports, then refuses new cases, then arms on stock" (terminal plan,
  organising principle). What was read names no record of the stock that the middle step would
  compare with.
- **Taking it.** The record that "refuses new cases" needs: the stock at the day a rule is
  promulgated, as a tracked file a change may only shrink, judged by the prior policy. For an
  existing repository at adoption, the same for tests that already fail.
- **Not worth taking if** the stock is small enough to arm each rule directly. Count the
  violations of each waiting rule across the fleet.

### 10. What a Change's documents cite is checked against the repository

- **Evidence.** gsd-core's drift guard: "planner and reviewer both read the same channel ...
  The fix must introduce an out-of-band source of truth: the project's own source code."
  Evagix checks documented commands against the repository. elephant-goldfish-model reports
  where documents and code diverge.
- **ETHOS today.** Links and command examples in documents are gated. The paths, commands and
  symbols that a design or a task cites are not resolved.
- **Taking it.** A gate dimension: each path and command cited in a Change's design and tasks
  resolves in the tree or the operation catalog, with the artifacts the Change itself creates
  excluded, and "cannot tell" reported as `unknown`.
- **Not worth taking if** the false blocks outnumber the catches: run it as a report over the
  archived Changes before it gates anything.

### 11. A budget for every text an agent loads

- **Evidence.** gsd-core pins each workflow and agent file to its byte size, so that growth is
  "a one-line reviewable diff". BMAD's test for a line: "would removing this line change agent
  behavior?", with pitfalls "from observed failure only".
- **ETHOS today.** The source budget requires limits for product and test code, and "other
  coordinates SHALL remain observations unless explicitly bounded". What was read bounds none
  for `AGENTS.md`, `rules/` and the skills as loaded context.
- **Taking it.** A declaration and a review criterion, perhaps no code: bound that coordinate,
  or pin each file's size; use the removal test when a rule or a skill is reviewed.
- **Not worth taking if** a coordinate for those paths is already bounded (the budget's
  declaration file was not read).

### 12. One page for the person who approves

- **Evidence.** qualitylayer's review page: why, where to start reading, each acceptance point
  with its evidence. OpenSpec's reviewing guide: an order that lets the reviewer stop early.
- **ETHOS today.** `ethos land --json` reports readiness. Nothing assembles intent, the entry
  point of the diff, the evidence, the deviations and the waivers for the approver.
- **Taking it.** A projection, derived from the Change, the commit range and the Attestations;
  and the reviewer's guide as a document now. It depends on item 3 for its best part.
- **Not worth taking if** approvers read the forge's own review page and want nothing else.

### 13. The forges' protection is observed against the declared roles

- **Evidence.** repo-policy: `audit` reads live settings against a declaration, `apply`
  re-reads before it reports success, and it prunes only what it owns by name.
- **ETHOS today.** Protected branch membership is derived "from the configured branch-role
  policy" (quality specification). "mandatory Forge admission" is open in the terminal plan.
  What was read observes no forge's own protection settings.
- **Taking it.** A read-only observation first, in the manner of `publish --observe-hosted`:
  does each peer protect the refs that hold the accepted and release roles as declared.
- **Not worth taking if** a requirement not read already defines that observation.

### 14. A claim about actual use names its measure, target, window and owner

- **Evidence.** ProductSpec separates checks before launch from "real-user behavior after
  launch", with a `provisional` target when the baseline is not yet known. One source, with
  Spec Kit's assessment asking for success metrics before delivery.
- **ETHOS today.** The contract requires observations bound to "the deployed identity,
  environment, baseline and observation window". Stage P6 is open and has no carrier.
- **Taking it.** A convention in the Change for the claim, and the Attestation of the reading
  to close it.
- **Not worth taking if** P6 is designed otherwise. The evidence is thin: one format, no use.

### 15. A reference of diagnostic codes, a way to say "this block was wrong", a page of failures

- **Evidence.** Evagix: one identity for a finding in every output, and an issue form for a
  false positive. OpenSpec lists its contract's known inconsistencies and has a command that
  files a report. loop-engineering catalogues how its own method fails.
- **ETHOS today.** Stable codes; an aim to measure "false admission, false blocking". No
  generated reference of the codes, no intake for a wrong block, no catalogue of failures.
- **Taking it.** Documents, and one generated page from the code catalog.
- **Not worth taking if** nobody but the present maintainers meets a block before 0.2.0.

## What ETHOS already does better than every source read

The first list is not to be read alone. Among what was read:

- **Effects are exact and re-observed.** Landing and publication by compare-and-swap, a
  recheck at the effect, a receipt before it. Spec Kit warns that an interrupted side effect
  "may still repeat"; OpenSpec's failed archive "is not a guarantee that files are unchanged";
  architekton "does not claim atomic publication". No source lands by compare-and-swap.
- **Evidence is durable, signed and bound.** Attestations bind commit, tree, policy, verifier
  and plane. CoaseEdge's receipt is "a same-workspace cache", Conductor's is a note the agent
  writes, ControlCoding's actors "are not authenticated people".
- **No stored state to rot.** gsd-core needed a decision record to rebuild its state file and
  loop-engineering lists "State Rot" among its failures. ETHOS persists Attestations and a
  four-field Lease.
- **The prior policy judges the change.** CoaseEdge runs the engine the candidate pins;
  only maintainer-contracts, like ETHOS, reads policy from the trusted base.
- **Admission for every write.** `lane prewrite` for exact paths under a Lease. CoaseEdge has
  one gate at the start; Kiro's and ControlCoding's hooks own their rules.
- **One law for a fleet.** The repository paradigm holds for every governed repository and
  one model generates both forges' pipelines. Every source governs one repository; CoaseEdge's
  contracts are opt-in for each.
- **Planes are kept apart and two forges get the same objects.** No source publishes one
  object to two forges or separates local, hosted and installed evidence as claims.
- **One typed continuation on every result.** CoaseEdge's stop advice, Spec Kit's gate step
  and BMAD's plan status are each one tool's form of it.
- **A previewed, resumable exit.** `ethos adopt --exit`. No source documents leaving beyond
  removing hooks or disabling an extension.

## Measured for ETHOS on 2026-11-18

Three of the questions below were measured the same day, on the release lane and on the governed
repositories with a checkout on the releasing host. The scripts read Git objects alone.

- **Distinct signers (question 1; item 1).** Over the last hundred commits of the accepted
  branch in sixteen governed repositories, the signing key was read from each commit's own
  signature. Fourteen repositories have exactly one key (one of them with fifty-eight unsigned
  commits among the hundred); one has two keys and two authors; one has three keys and one
  author. In fourteen of sixteen a check "the approver signed none of the range" would compare
  one key with itself. Item 1 therefore waits for an executor's key that differs from the
  person's, which is the approver key that the release gate's decision record defers to 0.3.0.
- **Intent and code in one commit (question 2; item 2, first step).** Over the last thousand
  non-merge commits of ETHOS's release lane, 352 change an open Change's proposal or delta
  specification, and 78 of those (22%) also change product source. A rule "a commit changes
  intent or code, not both" would have refused 78 commits of that history as written. Not
  measured: how often a Change's specification changed after its first code commit, and why.
- **Precision of agent reviews already run (question 4; item 7).** Five model reviews recorded
  before 2026-11-15 drew 28 comments, of which the lead judged 27 real. The measure is
  precision as judged by the change's own lead, taken from that day's record and not counted
  again; what the reviews missed is not measured.

Not measured: questions 3 and 5. For question 6, the titles of the accepted requirements and of
the open Changes were read, not their bodies: two open draft Changes already hold items 7 and
13, and no requirement title names requirement coverage or a path's overseeing role.

## Questions that only a measurement or the owner can settle

1. How many distinct signing identities act in each governed repository? (Item 1 is void with
   one.)
2. Over the archived Changes, how often did a Change's specs change after its first code
   commit, and why? (The form of item 2.)
3. On one archived Change, how many scenarios can be tied to a test in an hour, and how many
   prove uncovered? (Item 3.)
4. What was the precision of the agent reviews already run on this lane? (Item 7.)
5. How large is the stock of each rule that waits to be armed, across the fleet? (Item 9.)
6. Do the accepted requirements that this study did not read (it read eight of several
   hundred) already hold any of items 3, 6, 9 or 13?
7. Owner: is a boundary that a Change declares and that is only compared afterwards (item 5)
   within the accepted refusal of an "authored scope", or against it?
8. Owner: should intent before code (item 2) be a condition in ETHOS, an option for each
   repository, or remain a practice?
9. Owner: before 0.2.0 the kernel takes defect fixes only. Which of the documents and skills
   here (items 4, 7, 12, 15 and the first steps of 2 and 3) may enter as the weekly off-gate
   row, and in what order?
10. Owner: does ETHOS stay out of running agents? Items 7 and 8 fit as skills only if it does.
