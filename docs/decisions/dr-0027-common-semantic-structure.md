---
subject: ethos:decision:common-semantic-structure
role: decision
state: canonical
decision_id: DR-0027
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/repository-paradigm/spec.md
---

# DR-0027: Common Semantic Structure

Status: canonical rationale. The repository paradigm specification owns current behavior, and no
rule of this record is part of it until the Change that carries the rule lands.

Date: 2026-11-14.

Purpose: preserve why every governed repository follows one semantic structure, which three
invariants and seven rules state it, what the owner decided for the two rules that follow from no
invariant, and why the structure is reported before it refuses or blocks.

See also: [DR-0012: Repository paradigm](dr-0012-repository-paradigm.md), [DR-0011: Documentation
portability](dr-0011-documentation-portability.md), [DR-0017: One obligation, one
owner](dr-0017-one-obligation-one-owner.md), [DR-0026: The 0.2.0 release candidate gate is recorded
with three waivers](dr-0026-release-candidate-gate.md), [Module Layout
Rules](../../rules/module-layout.md) and the `structure-plan` and `common-base-plan` OpenSpec
Changes.

## Context

The owner asked on 2026-11-13 for the common semantic organization of every governed repository,
extracted from all of them and enforced as a strong constraint of the common base, so that
arbitrary, flat and unordered trees stop appearing. The requirement is older. On 2026-10-31 the
owner had asked that every file be organized by meaning in a reasonable directory, semantic
subdirectories included, that piled-up suffixes and scattered flat layouts be forbidden, and that a
file that must be split be organized into semantic subpackages by strong logic. A design answered
that request on the same day and was scheduled as two later Changes with a record of its own; this
record and the Changes of its design replace them.

The standing texts said the opposite. DR-0012 left product and domain structure, test organization
and documentation subject layout to each repository, and DR-0011 let each repository choose the
physical structure of its documentation. The paradigm specification therefore prescribed no product
structure and left every non-dot root directory to the repository, so no owner could judge a tree.

ETHOS's own tree shows them. At commit `b10254f87` it tracked 1,280 files in 266 directories outside
its archived Changes, 201 of those directories outside the protocol carriers. One root directory has
no declared meaning. Of the 47 directories outside the protocol carriers that hold one file, 23 are
gaps under the rule below that a directory holds more than one thing. 29 directories mix subject
subdirectories with 302 loose files, three directories only pass through to one child, and nine hold
more than 20 direct entries. A census of the governed repositories on 2026-11-13 found the same
shapes; it is unpublished, so this record states no figure for another repository.

With the direction, the owner decided the order on 2026-11-13: the structure is reported first, a
new violation is refused one release after the report, existing stock blocks after 0.2.0 on a dated
burn-down, a new direction queues behind the release-candidate path, and a frozen repository state
exists.

A committee of three seats reviewed the design: essence and contract, every governed repository, and
decidability with cost and order. It read three drafts over four rounds and approved the fourth
revision of the third, two seats approving and one approving with risks. Two of the seven rules
follow from no invariant, so the committee put them to the owner with one sentence of the product
design contract. The owner approved all three recommendations on 2026-11-14.

## Decision

- **Three invariants carry the rules.** Meaning at the root: every tracked root directory has
  exactly one meaning, its name states it, and the meaning is decidable from the tree and existing
  declarations. One home per responsibility: a shared responsibility has one root. Containment:
  depth expresses containment, so a directory exists because it holds two or more entries of one
  level, or because its name carries a responsibility or a key that its content cannot carry, or
  because its siblings are subjects of one level and it alone holds a single file, or because it is
  a container of subjects and a direct file is one of the container's kind only when a sibling
  subject holds a file of that kind anywhere in its subtree.
- **Two limits hold throughout.** No rule requires a directory to exist, so every repair merges,
  moves, renames or removes, and a file placed alone in a new directory is itself a gap. No rule
  compares one repository's subjects with another's, so subjects, their names and their number stay
  with each repository.
- **S1, the root is closed.** A non-dot root directory is a home whose name a shared responsibility
  binds, a source root of an applied ecosystem module, a product root that the profile declares with
  a name and a one-line purpose, or the directory that a package entry ships, which is the slot of a
  shipped Skill.
- **S2, one responsibility has one root.** The documentation, rules and Skills homes are single
  profile values, a record root lies under the documentation home, the root evidence home or the
  archive, and a home's name is reserved.
- **S3, a directory holds more than one thing.** A directory whose subtree is one file is a gap
  unless it is a home, a slot whose name is a key, a one-file Go package under a source root, or the
  only one-file subject of a container that has no other one-file subject and at least two subjects
  of two or more files.
- **S4, a container holds one level.** A directory that holds subject subdirectories holds, as
  direct files, only its set-asides: its index and the names of the paradigm's tool catalog. A
  direct file is a gap only when a sibling subject holds a file of the same kind and no descriptor
  set of its product root names it.
- **S5, width, is a count.** The rule would bound the direct entries of a directory at 20, raised to
  at most 30 with a reason for the whole repository. The owner decided on 2026-11-14 that no bound
  is armed. The report prints the number of direct entries of each directory, and the decision to
  arm is taken again after the first report shows the real numbers. No series declaration is built,
  and the parameter that would carry a bound ships only as the count's carrier.
- **S6, a name states a concept, is not built.** The owner decided on 2026-11-14 that the
  ambiguous-name list and the name checks of the 2026-10-31 design get one owner, the shared gate
  that the `common-base-plan` design ships for the language-neutral module layout rules. This
  record's Changes build nothing for it.
- **S7, no pass-through.** A directory that holds no file and exactly one subdirectory is a gap
  unless it is a root or a slot. S7 judges authored directories and leaves a package that holds only
  one child package to the Module Layout Rules.
- **Declarations carry evidence.** One value is new: a product root, declared in the profile with a
  name, a one-line purpose and a descriptor set, which adds every rule to that tree and switches
  none off. Three existing declarations reduce what a rule counts, and each holds only with its
  evidence: a record root, a normative source that is a direct file of the documentation home and
  reachable from its index, and a received path that a Git attribute marks and a source contract
  names. A declaration without its evidence excuses nothing. Containers, subjects, packages and
  slots are derived and never declared.
- **Report first.** The paradigm report lists structure gaps as latent gaps and leaves the verdict
  unchanged, and the status reader prints the count for each rule with the repository's map.
- **Refuse new, one release later.** One release after a recorded report on every repository that
  the burn-down table names, a commit or a landing is refused for a gap that its base tree does not
  hold. The check compares two trees and keeps no baseline file. Only S1, S2, S3, S4 and S7 can
  refuse, and no release refuses without shipping the preview of the repair.
- **Arm after 0.2.0.** A named Change names the release from which existing stock blocks, and holds
  the burn-down table: one dated row for each repository, by shape, count and owner, with producers
  before consumers. ETHOS repairs its own tree before any adopter's dated row. A frozen repository
  binds no arming release and keeps a row with its exit.
- **No code before 0.2.0, with one recorded exception.** Only the `structure-plan` Change, which
  carries this record and the design, lands before the stable release. After the stable release and
  the second landing of the history rebuild, the Change that moves ETHOS's documentation taxonomy is
  the first of this record's Changes and the report of S1, S3, S4 and S7 the second. That report
  alone may target beta.13, and only if the owner records that by 2026-11-28 and, at beta.13's
  landing on 2026-12-05, the documentation taxonomy Change and the report's other prerequisites have
  landed, its prepared patch has measured budgets, the
  product budget review has passed, the test budget step has landed and a run on disposable clones
  of every repository named by a dated row is recorded. It never enters beta.14, which is frozen.
- **Standing texts that this record succeeds.** In DR-0012, the Decision's clause that leaves
  product structure, test organization and documentation subject layout wholly to the repository,
  and the Consequences item that DR-0011 remains valid for documentation subject layout. The domain
  model, the subjects, names and axes of a layout, and the provider shape stay repository-owned.
- **Standing texts that this record narrows.** In DR-0011, the Decision's sentence that each
  repository chooses its physical structure and the two Consequences items that ETHOS cannot reject
  an adopter for lacking ETHOS-specific roots and that ETHOS's physical layout does not become an
  adopter requirement; with them the Docs Registry's paragraph that calls ETHOS's documentation
  shape a self-audit concern and the documentation root's sentence that the shape is not mandatory
  for adopters. What remains of them: subjects stay the repository's and no ETHOS root is required
  of an adopter, while S3, S4 and S7 apply inside every documentation home.
- **Standing texts that the later Changes amend.** In the paradigm specification, the requirements
  that product layout remains repository-owned, that the root carries only protocol entries, that
  received names keep their form, that conformance is a blocking verdict and that deterministic gaps
  carry a native repair, with the scenario that fixes the documentation taxonomy path. In the
  governance specification, the requirement that normative files remain distinct from directory
  roots. Each amendment arrives as a delta of the Change that ships its rule.
- **Standing texts that stay unless a successor arms more.** The Module Layout Rules' sentences that
  directory width and file count never authorize a split, the agent rule that repeats them and the
  evidence line of DR-0010 that cites them stand while S5 is a count. The Module Layout Rules'
  decision to retain a package that holds only child packages stands while S7 leaves packages alone.
- **The contract sentence.** The owner approved the sentence quoted below for the paragraph of the
  product design contract that today says the paradigm fixes only shared carriers, with that
  paragraph's link kept, and approved naming the paradigm beside the Module Layout Rules as the
  owner of the three invariants. The contract changes in the Change that ships the first rule,
  together with the paradigm specification, and not in the planning Change.

> This is not product cloning: each repository keeps its domain model, the subjects, names and axes
> of its layout, and its provider shape; the ETHOS source repository paradigm fixes the shared
> carriers and, for the directories a repository authors, three invariants: each root states its
> meaning, each shared responsibility has one home, and depth expresses containment.

## Alternatives Rejected

- **A closed vocabulary of planes:** rejected because one table would name every root and second
  level, so path equality would again stand for meaning, which DR-0011 rejected; each mixture would
  need a kind of its own, which DR-0017 rejected; and the contract's three questions for a new
  carrier fail.
- **Invariants only, with no home and no declaration:** rejected because it is the smallest design
  but cannot close the root or give a responsibility one home, the first two findings of the census.
- **A declared map for each repository:** rejected because it is a second tree over every directory
  and a copied template, which DR-0017 rejected, and it is the place where exceptions get written.
- **Arming a width bound now:** rejected by the owner on the committee's recommendation, because a
  bound reverses the Module Layout Rules' sentence that width is never split authority, a metric can
  be met by a meaningless split with review the only guard, and the default came from a census that
  counted another unit.
- **Building the name list in this family:** rejected by the owner on the committee's
  recommendation, because the shared gate of the common base already takes the language-neutral
  naming rules, so one obligation would have two owners.
- **A contract value for a root whose layout another product fixes:** rejected because it decided
  nothing or switched blocking off. The product root's purpose line names that product instead, and
  every rule still runs.
- **A stricter documentation index and a test-axis rule:** rejected for this family because the Docs
  Registry owns the index and blocks on it today, and a test tree is a container tree that S1, S3,
  S4 and S7 already judge.
- **Blocking existing stock at once, or freezing it in a baseline file:** rejected because the owner
  fixed the order of report, refusal and arming, and because a gap's identity, its obligation and
  its directory, lets two trees decide what is new without a stored baseline.
- **Amending the contract in the planning Change:** rejected because the sentence states what the
  paradigm fixes in the present tense, while the paradigm specification would still say that product
  layout is repository-owned until the first rule ships.

## Consequences and Boundary

- Nothing changes for any repository when this record lands. The paradigm specification states
  current behavior until each Change delivers its rule.
- After the report ships, a repository sees its gaps without a changed verdict. After refusal ships,
  it cannot add a gap under S1, S2, S3, S4 or S7. After arming, it cannot bind the arming release
  with stock outside its record roots.
- Review keeps what the tree cannot decide: a second root for one responsibility under another name,
  the test axis, a name that states no concept and one concept under two names.
- While S5 only counts, a flat wide directory is the cheapest conforming tree after refusal ships.
  This route is stated and not closed.
- Repair is mostly the owner's choice. Few moves are deterministic, and imports are left to each
  ecosystem's rename tool and the lane's proof.
- Records do not move. A published path moves only with a changelog entry that names the old and the
  new path, and ETHOS adds no redirect.
- The design estimates about 1,080 product and 1,170 test line-equivalents for the seven later
  Changes. The tests need a successor step of DR-0023, and the report Change alone crosses the
  product review point of DR-0025. Each estimate is replaced by a measured delta before its Change
  opens.
- After arming, one defective rule blocks every adopter at once.
- This record adds no checker and is not edited after acceptance. Arming S5, building S6 here or
  arming S7 against packages is a successor record that names this one.

## Evidence and Revisit

- The design of the `structure-plan` Change holds the model, each rule's full text with its excuses,
  ETHOS's stock for each rule, the repair, the order and the cost table.
- Every figure in this record and in the design is ETHOS's own, measured at commit `b10254f87`. The
  committee's closing record and the reviews are local documents; this record is their tracked form.
- The owner's approval of 2026-11-14 covers the three recommendations and nothing else: S5 as a
  count, S6 folded into the shared gate, and the contract sentence.
- Not established: a tracked owner for the frozen state; the trees of three repositories without a
  local checkout; the contents of the unpublished census; whether the commit hook fires on the
  commit that concludes a merge; the run time of the two-tree check on the largest tree; and any
  count for the composition-file clause of S4, which ETHOS's tree does not exercise.

Revisit when the first report shows the real width numbers, when the shared gate takes the name
list, when a governed repository shows a tree that the invariants cannot judge without an exception,
or when a Change's measured delta departs from its estimate. Retire this record when the paradigm
specification states the invariants, the rules and these rejected alternatives itself.
