# Design

## Context

Measured on `dev` and on 14 governed repositories of the releasing host on 2026-11-15; the three
research pages of this Change hold the figures and the sources.

- **Intent leaves by the side doors.** 248 follow-up bullets and 96 withdrawn tasks sit in archived
  Changes, which the specification says own no queue. 174 of 353 archived Changes change no
  requirement; the largest of them are designs that span many later Changes, and an archive is
  immutable while such a design is still the current one. The rows of the release-candidate gate
  are prose in a decision record and a list in an untracked script. Defects, rulings and proposals
  of a week sit in one session's untracked notes and in agent memory.
- **A session is not a carrier.** On 2026-11-15 a request failed and a session lost two hours and
  seventeen minutes. What was in files, detached processes and pushed refs was intact. What the
  session alone held was gone.
- **The plan mixes two lifetimes.** The terminal plan holds the order of unfinished work and, in
  about 260 of its 500 nonblank lines, the architecture of the end state. It and the contract stand
  at the default bound of 500; the repository's bound is 560 until the command reference splits.
- **No common shape.** 9 documentation homes use 20 first-level names, four forms of plan, four
  forms of contract and two of research. Two homes carry no role metadata.
- **The ignored build tree has the same disease.** ETHOS's holds 14 GB: 77 purpose directories
  under `build/runtime/work`, 29 of them untouched for a week, one of them 10.5 GB of clones; 56
  loose files at the root of `build/evidence`; a directory that the topology does not name.
- **Practice elsewhere** (primary sources, read 2026-11-15): a proposal is one document with an
  identity; acceptance is not scheduling; the design is a record and execution another object; a
  roadmap that is hand-kept goes stale, so entries are thin pointers to tracked objects or the
  view is generated. No tracker meets the constraints, and OpenSpec's maintainers answer requests
  for a backlog with a Change that holds only a proposal.
- **The owner decided on 2026-11-15**: the common law and mechanisms come from ETHOS; a decision
  record that contradicts the end state is replaced; there is no backlog; the review's unanimous
  final text settles the rest; and the build tree is brought to one shape as well.

Revision 1 answered with new carriers. Two of the three seats blocked it, and the contract already
held the test that it failed.

## Goals / Non-Goals

Goals:

- Everything that must outlive a session is in the tracked carrier of its kind.
- ETHOS provides the carriers and the rules once for every governed repository.
- A reader finds the end state, what is committed and in what order, what is proposed and the
  evidence behind each, from the repository alone.
- No state is written twice: what a reader can derive is derived.

Non-Goals:

- A backlog, an inbox or a feedback registry, in ETHOS or in a governed repository.
- A new carrier, schema or lifecycle state where an existing one holds the obligation.
- A fixed tree of subjects. Subjects, their names and their number stay with each repository.

## Decisions

### 1. The contract's test decides: no new carrier

The contract admits a carrier, a persisted record or a lifecycle state only when the obligation is
absent from OpenSpec, Git and the existing carriers, when deleting the entity would make an
invariant unprovable, and when it has one owner and an end. Applied to what revision 1 proposed:

| Entity of revision 1                 | Absent elsewhere                                          | Verdict      |
| ------------------------------------ | --------------------------------------------------------- | ------------ |
| An intake of short files             | no: a Change without tasks holds it                       | not admitted |
| A `proposals` home with six states   | no: a draft's proposal and design hold it                 | not admitted |
| A roadmap file of rows with an order | no: the plan owns order, and a Change names what it needs | not admitted |
| A documentation tier of the proof    | it is the fast tier's subject                             | not here     |
| A path class for direction writes    | no: admission already lets a lane create a Change         | not admitted |

What was missing is not a carrier. It is the use of the carriers that exist, three sentences of
law that kept them from being used, and the readers that make their content visible.

### 2. Where each thing lives

| What must last                              | Its carrier, which exists                         | What was missing                               |
| ------------------------------------------- | ------------------------------------------------- | ---------------------------------------------- |
| The end state                               | the contract's numbered invariants                | a reader's command and terminal value for each |
| The order of unfinished work, and its exits | the terminal plan                                 | room, and the gate's rows by name              |
| An idea, a defect's repair, a wish          | a draft: an OpenSpec Change without tasks         | the rule that a draft may stay open            |
| A design that spans Changes                 | a draft with a design, active while it is current | the same rule; it was archived too early       |
| A deferred task or a follow-up              | the draft that will carry it                      | a draft at the moment of deferral              |
| A ruling by the owner or the lead           | the Change it rules on, or a decision record      | the habit; rulings sat in chat and notes       |
| A finding about the world                   | a research study under the documentation home     | a review date, and the habit                   |
| An observation of a run                     | its Attestation or the forge's record             | nothing                                        |
| An agent's lesson                           | the rule, tool or test that it corrects           | nothing new; memory is a cache                 |

### 3. Drafts

OpenSpec has the object: a Change without tasks validates strictly with `skip_specs`, and its
list and view name it a draft (probed on 2026-11-15 with the installed 2.0.0). A lane may create a
Change's files without another Change, so a draft costs one commit in the lane a writer already
holds, and its lane's proposal ref makes it durable on both forges before it lands. It lands with
that lane's batch under the existing proof.

- **A draft may stay open.** It is intent, not unfinished work. The readers list drafts apart
  from Changes in work, each with its age in releases.
- **A draft is disposed in the contract's four ways, and only by a commit to it.** Accepted: it
  gains its tasks, with their acceptance and proof, and the plan names it. Superseded: it is
  archived with the name of the later Change or decision on the same subject. Pending
  verification: it stays, and its proposal names the missing fact, the contradiction or the gap.
  Rejected: it is archived with the reason. The governing Change of a draft is the draft, so the
  archive keeps what the contract asks to keep.
- **A design draft stays active while it is the current design.** It is edited as its members
  land and archived when the last has landed and its lasting content is settled: the decision in
  a record, the order in the plan, the explanation in the architecture pages.
- **A deferral creates its draft.** A task withdrawn under DR-0016 for later work, and a follow-up
  that is work and not an observation, name the draft that carries them. Nothing waits in an
  archive.
- **An idea that is not worth a draft is let go.** No other list holds it.

### 4. The roadmap is the plan and a derived view

The contract gives the plan the order of unfinished work and forbids a queue, a dependency ledger
and a stored graph. Both stand.

- **The plan divides by lifetime.** Its architecture section moves to the architecture pages, by
  subject. The plan keeps the order, the dependencies, the exits and the rules of convergence,
  and gains the gate's rows by the name of their Changes, grouped by release.
- **A row's state is read, never written.** For the tree that is read: landed when a Change of
  that name is archived, in work when it is active with tasks, drafted when it is active without,
  and open otherwise. A ref on a forge is a separate observation and no state. A row with two
  Changes names both; a waived row names its record.
- **A release is the unit of time.** A cut is a dated release heading of the changelog. When a
  release is tagged its landed rows leave the plan, and the changelog and the tag keep them, so a
  pruned archive misreads nothing.
- **The execution plan of a release is its release Change**, opened as a draft when the release
  before it is tagged, with the Changes of its batch as its tasks.

### 5. The end state is the contract's invariants, each with a reader

The contract's fifteen invariants are the end state. The plan's completion boundary states, for
each invariant by number, the command that reads it and the value that means done. Today's value
is printed by the reader for one tree and one product version and is stored nowhere; a value that
no command reads yet is printed as unread, never as zero. An invariant changes by the owner's
decision alone.

### 6. Research is built as a role

The role and its home exist. A study states its question, the date and URL of each source,
findings apart from inference, what it could not reach and what it informs. It gains one field, a
review date as data, which the documentation reader reports when it has passed. A study that a
decision cites is not edited; a newer study supersedes it through the existing state. The
committee's fact bases, the censuses and the pre-tag readings are research and are written there,
not in a work directory. The lifecycle and dossier template that one governed repository already
keeps are inputs to the role's page in the documentation contract.

### 7. Role homes: the first level of a documentation home names a role

DR-0027 rejected a closed vocabulary of planes for three reasons, and the owner's direction of
2026-11-15 on the same subject is later. This design answers the reasons and keeps the change
narrow.

- **The rule.** A first-level directory of a documentation home is the home of one document role,
  and ETHOS fixes its name from the role vocabulary that the documentation contract already has.
  Below it a repository keeps its own subjects. A role without documents has no directory. A file
  at the home's root stays where DR-0027 admits it.
- **Path projects metadata.** The role is declared in each document; the directory is derived
  from it. The check is that a document's first-level directory is the home of its declared role,
  so path equality does not stand for meaning, which was the first reason.
- **A mixture splits.** A directory of two kinds is two kinds of document, and each file maps by
  its own role with a preview for each file, so no mixture needs a kind of its own, which was the
  second reason.
- **No carrier is added.** A name is fixed, not an entity, so the three questions do not arise,
  which was the third.
- **Exempt by role or by toolchain.** Evidence under a documentation home is reported as
  belonging to the record root. The taxonomy and generated views follow DR-0027's design. A home
  that another documentation toolchain builds is exempt until the documentation contract states
  how it declares a role. A repository without a documentation home is asked for nothing. An
  asset sits beside the document that uses it or under one asset name.
- **The table of names is the fleet step's work**, written with the fleet seat's per-file reading
  before that step's Change is written. No governed repository keeps a backlog tool's tree; the
  one that does disposes each open task as a draft or a closed item in its own lane.

### 8. The session rule

One sentence replaces the contract's sentence on transcripts and memory and the plan's matching
ones, so the contract does not grow:

> A session, an agent's memory and an ignored directory authorize nothing. Losing all three loses
> no obligation, ruling, finding or design: each is in the tracked carrier of its kind, an
> observation in its Attestation, and a successor that reads only those reaches the same next
> action.

The agent rules gain the procedure: at each operation boundary an agent names what exists only in
its session and writes it to the carrier of its kind.

### 9. The build tree

The topology already names the homes of the ignored build tree: tool caches, work, artifacts,
evidence and ETHOS's own output. Three things below that level have no rule, and the session rule
gives the first.

- **Nothing in the build tree is the only copy of what must last.** A design, a ruling, a study
  or a tool that others run is tracked; the build tree keeps what a command can produce again,
  and evidence with a named consumer and an exit.
- **A work directory has an owner and ends with it.** It is named by the lane or the session that
  owns it and is retired with that lane, or when its content has been sunk to a carrier. A purpose
  directory with no owner is residue.
- **Evidence is a directory for each subject**, with its consumer and exit; no file lies loose at
  the root of the evidence home. A name the topology does not declare is not created.

The mechanism belongs to rows the gate already has: the residue classes, the proof's scratch
output and store retention. This design adds their input: the reader prints, for each home, the
count, the size and the oldest entry. ETHOS applies it to its own tree first.

### 10. The law that changes, sentence by sentence

| Text                                                                     | What happens                                             | Step |
| ------------------------------------------------------------------------ | -------------------------------------------------------- | ---- |
| The contract: OpenSpec is the sole intent, design and dependency carrier | stands; the design now obeys it                          | none |
| The contract: no queue, dependency ledger or stored graph                | stands; the roadmap view is derived                      | none |
| The specification: two design authorities; archives own no queue         | stands                                                   | none |
| The plan: no backlog and no feedback registry                            | stands                                                   | none |
| The contract and the plan: transcripts and memory as context             | replaced by the session rule's sentence                  | 2    |
| The plan's rules of convergence                                          | one sentence added: a draft is open by rule              | 2    |
| DR-0016: a withdrawn task returns as a new Change when taken up          | a successor sentence: its draft exists at the withdrawal | 2    |
| The OpenSpec configuration's rule on follow-ups                          | a follow-up that is work names its draft                 | 2    |
| The plan itself                                                          | divides; gains the rows by name                          | 3    |
| DR-0027's sentence that names and axes stay with each repository         | a successor for the first level of a documentation home  | 5    |
| The specification's scenario on product extension roots                  | amended with it                                          | 5    |
| The documentation contract's portability boundary                        | amended with it; ships with the code that reports        | 5    |
| The documentation contract's research role                               | gains the review date, with its reader                   | 4    |

DR-0011's remaining sentences were succeeded by DR-0027. No rule binds a governed repository
before the Change that carries its reader has landed.

### 11. Alternatives considered

- **New carriers for intake, proposals and roadmap (revision 1):** rejected by the contract's
  three questions and by the owner's decision against a backlog.
- **A tracker tool:** none meets the constraints; the tool study holds the reasons.
- **Keep DR-0027 whole and unify by metadata only:** it costs no move, and it leaves nine homes
  with twenty names, which is what the owner asked to end. Kept as the fallback if the review does
  not sign decision 7: then role metadata is completed everywhere and one reader lists every
  home by role.
- **Do nothing before 0.2.0:** rejected by the owner's direction; steps 1 to 3 change text and
  ETHOS's own tree only.

### 12. Order and cost

| Step | What                                                                                                                     | Class                         | Product, tests | When                         |
| ---- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------- | -------------- | ---------------------------- |
| 1    | this design, reviewed to one signed text; it stays an active draft                                                       | no rule                       | 0, 0           | now                          |
| 2    | the text of decision 10's step 2                                                                                         | ETHOS's own law               | 0, 0           | an off-gate row before 0.2.0 |
| 3    | ETHOS's tree: the plan divides; every open note, follow-up and withdrawn task is disposed once; the build tree is sorted | no rule; a few path constants | about 3, 3     | off-gate rows before 0.2.0   |
| 4    | readers: drafts by age, rows by state, research past review, build homes                                                 | new code, no refusal          | about 170, 200 | after the test budget step   |
| 5    | the fleet: role homes, research fields and build homes as reporting obligations, with previews                           | a new rule, reporting         | about 190, 230 | after 0.2.0, with DR-0027's  |

The figures for steps 4 and 5 are the decidability seat's, within 40 percent, from measured
commits of similar shape. Steps 4 and 5 do not fit the test ceiling's 247 free lines without the
prepared budget step. Step 3 moves 23 tracked mentions of the plan's path, five of them in
documents an installation carries, one constant in the audit and two tests that pin the path.

### 13. Review record

- **Revision 1**, commit `ae42de7cb`: a fourth object for intake, a `proposals` home, roadmap rows
  as a file, a documentation tier and direction paths.
- **Fleet seat on revision 1: approve with conditions.** Taken: mapping by file kind with a
  preview for each file, exemptions by role and by toolchain, the corrected census, the order of
  the fleet's moves, and no second intake in any repository.
- **Essence seat on revision 1: block.** The law that the design changed was not listed; role
  homes contradicted DR-0027 without an answer; the contract's three questions were unanswered;
  the dispositions were not the contract's. Taken: decisions 1, 3, 7, 8 and 10, and the end state
  as the contract's invariants.
- **Decidability seat on revision 1: block.** The documentation tier does not exist and is no
  narrowing; a class by a file's content is not decidable at admission; the claim that step 2
  changes no rule was false; two states read outside the tree. Taken: no tier and no path class;
  each change of law has its step; a state is read from one tree and a cut is a release.
- **Owner after revision 1:** no backlog; the review's unanimous final text decides the rest; the
  build tree is brought to one shape.
- **Revision 2**, commit `25a6925a4`: the intake and the `proposals` home removed.
- **Revision 3** is this text.

## Risks / Trade-offs

- **Drafts that pile up are a backlog by another name.** A draft costs a proposal that validates,
  the reader prints their count and the oldest age, and a rejected draft leaves by its archive.
- **Open Changes on the accepted branch.** A draft is open by rule; the reader keeps it apart from
  work so that an unfinished Change stays visible as one.
- **Role homes move files.** The fleet seat counted the mentions: 49 in ETHOS for three
  directories, and 715 in the two repositories under repair. The step reports first and moves a
  repository in its own lane.
- **The plan's division moves carried paths.** A move of a path that an installation carries is a
  release entry.
- **Cost before 0.2.0.** Steps 2 and 3 take off-gate slots that other rows wanted.

## Open Questions

- Which off-gate slots do steps 2 and 3 take, beside the gate record that holds the first?
- Are the 248 follow-ups and 96 withdrawn tasks disposed one by one, or only those that a current
  reader still needs?
