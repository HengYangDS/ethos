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
  about 90 of its 500 nonblank lines, the architecture of the end state. It and the contract stand
  at the default bound of 500; the repository's bound is 560 until the command reference splits.
- **No common shape.** 9 documentation homes use 20 first-level names, four forms of plan, four
  forms of contract and two of research. Two homes carry no role metadata.
- **The ignored build tree has the same disease.** ETHOS's holds 14 GB: 77 purpose directories
  under `build/runtime/work`, 29 of them untouched for a week, one of them 10.5 GB of clones; 56
  loose files at the root of `build/evidence`; a directory that the topology does not name.
- **Decisions do not show their reasoning.** By text presence on the accepted branch of 13 governed
  repositories: the share of designs that name an alternative runs from a fifth to all of them
  (ETHOS: 124 of 359); a design that cites a study or an outside source is rare (ETHOS: 9 of 359;
  none in six repositories); ten repositories hold no research document.
- **Practice elsewhere** (primary sources, read 2026-11-15): a proposal is one document with an
  identity; acceptance is not scheduling; the design is a record and execution another object; a
  roadmap that is hand-kept goes stale, so entries are thin pointers to tracked objects or the
  view is generated. No tracker meets the constraints, and OpenSpec's maintainers answer requests
  for a backlog with a Change that holds only a proposal.
- **The owner decided on 2026-11-15**: the common law and mechanisms come from ETHOS; a decision
  record that contradicts the end state is replaced; there is no backlog; the review's unanimous
  final text settles the rest; the build tree is brought to one shape as well; and ETHOS and the
  governed repositories strengthen research, analysis, comparison, trade-offs, reasons and scope
  of application.

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

| What must last                              | Its carrier, which exists                     | What was missing                               |
| ------------------------------------------- | --------------------------------------------- | ---------------------------------------------- |
| The end state                               | the contract's numbered invariants            | a reader's command and terminal value for each |
| The order of unfinished work, and its exits | the terminal plan                             | room, and the gate's rows by name              |
| An idea, a defect's repair, a wish          | a draft: an OpenSpec Change without tasks     | the rule that a draft may stay open            |
| A design that spans Changes                 | a Change with its design and one open task    | the same rule; it was archived too early       |
| A deferred task or a follow-up              | the draft that will carry it                  | a draft at the moment of deferral              |
| A ruling by the owner or the lead           | the Change it rules on, or a decision record  | the habit; rulings sat in chat and notes       |
| A finding about the world                   | a research study under the documentation home | a review date, and the habit                   |
| An observation of a run                     | its Attestation or the forge's record         | nothing                                        |
| An agent's lesson                           | the rule, tool or test that it corrects       | nothing new; memory is a cache                 |

### 3. Drafts

OpenSpec has the object: a Change without tasks validates strictly with `skip_specs`, and its
list and view name it a draft (probed on 2026-11-15 with the installed 2.0.0). A lane may create a
second Change beside its own, in a commit that holds only that Change's paths and selects no
other; its proposal ref makes the draft durable on both forges. A draft is never the Change a
proof selects: it lands beside a Change in work, under that Change's proof, and is archived only
once it holds a design and one checked task that records its disposition. Native selection does
not tell a lane's own Change from an inherited one, so while a branch holds an open Change, every
lane command names its Change with `--change`. Step 4 ends that price. In a governed repository
no draft enters the accepted branch before step 4 has landed, unless every session that writes
there names its Change in every lane command and commit, with `--change` or `ETHOS_CHANGE`.

- **A draft may stay open.** It is intent, not unfinished work. The readers list drafts apart
  from Changes in work, each with its age in releases.
- **A draft is disposed in the contract's four ways, and only by a commit to it.** Accepted: it
  gains its tasks, with their acceptance and proof, and the plan names it. Superseded: it is
  archived with the name of the later Change or decision on the same subject. Pending
  verification: it stays, and its proposal names the missing fact, the contradiction or the gap.
  Rejected: it is archived with the reason. The governing Change of a draft is the draft, so the
  archive keeps what the contract asks to keep.
- **A design stays active while it is the current design.** It may hold tasks of its own, such as
  its review, and then reads as a Change in work. It keeps one open task, its settlement, because
  a Change whose tasks are all checked is complete and takes no further edit. It is edited as its
  members land and archived
  when the last has landed and its lasting content is settled: the decision in a record, the
  order in the plan, the explanation in the architecture pages.
- **A deferral creates its draft.** A task withdrawn under DR-0016 for later work, and a follow-up
  that is work and not an observation, name the draft that carries them, whose proposal names
  its owner by role, its next action and the release at which it is read again. Nothing waits in
  an archive.
- **An idea that is not worth a draft is let go.** No other list holds it.

### 4. The roadmap is the plan and a derived view

The contract gives the plan the order of unfinished work and forbids a queue, a dependency ledger
and a stored graph. Both stand.

- **The plan divides by lifetime.** The lines of its `Architecture` section that describe the end
  state move to the architecture pages, by subject. The plan keeps the order, the dependencies,
  its eight batches with their exits and the rules of convergence,
  and gains the gate's rows by the name of their Changes, grouped by release.
- **A row's state is read, never written.** For the tree that is read: landed when a Change of
  that name is archived, in work when it is active with tasks, drafted when it is active without,
  and open otherwise. A ref on a forge is a separate observation and no state. A row with two
  Changes names both and is landed only when both are; until then the reader prints each. A
  waived row names its record, reads as waived and is not counted among the rows left.
- **A release is the unit of time.** A cut is a dated release heading of the changelog. When a
  release is tagged its landed rows leave the plan, and the changelog and the tag keep them, so a
  pruned archive misreads nothing.
- **The execution plan of a release is the plan's rows under that release.** Its release Change
  keeps the release's own steps as its tasks and copies no row.

### 5. The end state is the contract's invariants, each with a reader

The contract's fifteen invariants are the end state. The plan's completion boundary states, for
each invariant by number, the command that reads it and the value that means done. Today's value
is printed by the reader for one tree and one product version and is stored nowhere; a value that
no command reads yet is printed as unread, never as zero. An invariant changes by the owner's
decision alone.

### 6. Research is built as a role

The role and its home exist. A study states its question, each source, findings apart from
inference, what it could not reach and what it informs. A source is of two kinds: one outside the
repository, with its URL, date and version, or a measurement of the repository's own, with its
path, its date, what was measured and a digest of it. A check that counts only outside sources
would call the weightiest evidence of a product repository no research. It gains one field, a
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
- **What serves another document stays with it.** A document whose declared role is `index`
  indexes its own directory and stays there; a `template` and an asset sit beside what they
  serve. A repository's declared normative sources and product roots keep their paths. A home
  without role metadata completes it first, which is the fallback's work, before the check
  reports it. A directory's index is judged by its directory, a file at the home's root by
  DR-0027 alone, and a document without a role by the registry's existing gap; none is a gap of
  this check. A role home is a home under DR-0027's rule on one-file directories.
- **A mixture splits.** A directory of two kinds is two kinds of document, and each file maps by
  its own role with a preview for each file, so no mixture needs a kind of its own, which was the
  second reason.
- **The three questions are answered.** One table is added to the paradigm, from role to name:
  no carrier fixes where a role's documents live, without it one role cannot be shown to have one
  home across repositories, and the paradigm owns it while the role stands.
- **Exempt by role or by toolchain.** Evidence under a documentation home is reported as
  belonging to the record root. The taxonomy and generated views follow DR-0027's design. A home
  that another documentation toolchain builds is exempt until the documentation contract states
  how it declares a role. A repository without a documentation home is asked for nothing. An
  asset sits beside the document that uses it or under one asset name.
- **The table of names is the fleet step's work**, written with the fleet seat's per-file reading
  before that step's Change is written.
- **No governed repository keeps a backlog tool's tree.** In the one that does, the open tasks
  become drafts, its decisions become decision records, its documents move to the documentation
  home, its milestones go to the plan, and completed and archived tasks are removed, since Git
  keeps them. The session that holds its lane does it, after the repair and under decision 3's
  condition, and no other repository
  adopts a backlog tool.

### 8. The session rule

One sentence replaces the contract's sentence on transcripts and memory and the plan's matching
ones, and step 2 holds the contract at 500 nonblank lines:

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
- **A work directory has an owner and ends with it.** It keeps its purpose's name, as the
  configuration reference says, and belongs to one lane or session; how that owner is read is the
  owner mark that the host reservation row's second Change designs. It is retired with its
  owner, or when its content has been sunk to a carrier. A purpose
  directory whose owner cannot be read is unknown, never residue: the reader reports it, and only
  an explicit, previewed step releases it.
- **Evidence is a directory for each subject**, with its consumer and exit; no file lies loose at
  the root of the evidence home. A name the topology does not declare is not created. A path
  that a repository's documented command or its own tool writes is reported with that producer as
  the repair, and a product's documented output maps to the artifacts home.

Each of these rules reads one host and not a tree, so none is a reporting obligation, and no row
of the gate owns the work home today. Step 4's reader observes it: for each home it prints the
count, the size and the oldest entry, with the owner where one can be read. ETHOS applies the
rules to its own tree first.

### 10. A decision shows its reasoning

- **Rests on.** The reasoning census of 2026-11-15 (the fleet census page holds it): presence of
  the form by text, not its quality. The practice study: proposal processes keep alternatives,
  prior art and open questions under fixed headings inside the proposal.
- **Considered.** A free-form design, as today: a third of ETHOS's designs name an alternative,
  and nothing can list the ones that do not. A separate analysis document for each decision: a
  second carrier beside the design, refused by decision 1. Fixed parts inside each decision,
  which a reader can list and a reviewer can judge.
- **Chosen because.** The carriers already ask for most of it: a design explains alternatives and
  rationale, a decision record has its five sections, a study has sources. What is missing is that
  each single decision carries its own parts, so that an absent part is visible. The price is
  form: four labelled parts make a short decision longer.
- **Applies to** every decision of a Change's design, which the design numbers so that a reader
  finds each, every decision record and every
  ruling that a Change records. It does not apply to a Change without a design, such as a defect
  with one sensible repair, which states its cause; nor to a design written before the rule.

The four parts, as this decision shows them:

| Part           | Holds                                                                                      | The owner's word   |
| -------------- | ------------------------------------------------------------------------------------------ | ------------------ |
| Rests on       | the study or measurement the choice depends on, or that it depends on none and why         | research, analysis |
| Considered     | the alternatives compared, each with what it costs                                         | comparison         |
| Chosen because | the reason, and the trade-off that is accepted with it                                     | trade-off, reason  |
| Applies to     | where the decision holds, and what it does not cover, named, or that no exception is known | scope              |

A choice that rests on facts outside the repository (a tool, a standard, others' practice) or on
a measurement names its study under the research home; the study carries the analysis and, where
the question is a choice, the comparison. A decision record keeps its five sections, which hold
the same parts for a choice that outlives its Change. A ruling given in a session is written into
the Change it rules on, with its reason and its scope. A value that several repositories use, such
as a threshold, has one study in the repository that produces it, and the others cite that study
and do not restate it.

The form is a schema that a reader checks, so it answers the contract's three questions. OpenSpec's
design instruction already asks each decision for its rationale and its alternatives; no carrier
asks a design's decision what it rests on or where it applies, and none lets a reader list an absent
part. Without labelled parts no reader can show that a decision has them; a free text can only be
judged by reading it. The OpenSpec configuration's rule for a design owns the form, and the form
ends when OpenSpec's own template carries such parts.

Presence is decidable and quality is not. A decision is each third-level heading, or each top-level
list item, directly under the design's `Decisions` section. A part is a list item under it whose
first words, in strong type, are the label. The rule binds a Change created on or after the date it
states. The reader of step 4 lists each such decision without a part and never refuses, because no
repair can write a reason; the review judges the content. ETHOS writes the form once, in its
OpenSpec configuration's rule for a design and in the research role's page of the documentation
contract, and step 5 brings it to every governed repository as a reporting obligation.

### 11. The law that changes, sentence by sentence

| Text                                                                                                                                         | What happens                                                                                | Step |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---- |
| The contract: OpenSpec is the sole intent, design and dependency carrier                                                                     | stands; the design now obeys it                                                             | none |
| The contract: no queue, dependency ledger or stored graph                                                                                    | stands; the roadmap view is derived                                                         | none |
| The specification: two design authorities; archives own no queue                                                                             | stands                                                                                      | none |
| The plan: no backlog and no feedback registry                                                                                                | stands                                                                                      | none |
| The contract and the plan: transcripts and memory as context                                                                                 | replaced by the session rule's sentence                                                     | 2    |
| The plan's rules of convergence                                                                                                              | one sentence added: a draft is open by rule                                                 | 2    |
| DR-0016: a withdrawn task returns as a new Change when taken up                                                                              | a successor sentence: its draft exists at the withdrawal                                    | 2    |
| The OpenSpec configuration's rule on follow-ups                                                                                              | a follow-up that is work names its draft                                                    | 2    |
| The plan itself                                                                                                                              | divides; gains the rows by name                                                             | 3    |
| The plan's completion boundary: no active proposal may remain                                                                                | amended: a draft and a current design are open by rule                                      | 3    |
| The OpenSpec configuration's rule for a design                                                                                               | each decision carries its four parts                                                        | 2    |
| DR-0027's sentence that names and axes stay with each repository                                                                             | a successor for the first level of a documentation home                                     | 5    |
| The specification's scenario on product extension roots                                                                                      | amended with it                                                                             | 5    |
| The documentation contract's portability boundary                                                                                            | amended with it; ships with the code that reports                                           | 5    |
| The documentation contract's research role                                                                                                   | gains the review date and the study's parts, with reader                                    | 4    |
| The specification's scenario, the documentation contract's sentence and DR-0027's remainder that an adopter need not reproduce an ETHOS root | amended: no role, no directory                                                              | 5    |
| The artifact topology                                                                                                                        | states decision 9's rules in its boundary and cleanup text; no prefix, rule or home changes | 3    |
| The agent rules and the OpenSpec configuration's withdrawal rule                                                                             | amended with them                                                                           | 2    |
| The specification's scenario that a new lane selects the active Change it inherits                                                           | amended: selection prefers a Change the lane created to one it inherited                    | 4    |
| The repository paradigm                                                                                                                      | gains the role-to-name table and the reporting obligation for a decision's parts            | 5    |

DR-0011's remaining sentences were narrowed by DR-0027. No rule binds a governed repository
before the Change that carries its reader has landed.

### 12. Alternatives considered

- **New carriers for intake, proposals and roadmap (revision 1):** rejected by the contract's
  three questions and by the owner's decision against a backlog.
- **A tracker tool:** none meets the constraints; the tool study holds the reasons.
- **Keep DR-0027 whole and unify by metadata only:** it costs no move, and it leaves nine homes
  with twenty names, which is what the owner asked to end. Kept as the fallback if the review does
  not sign decision 7: then role metadata is completed everywhere and one reader lists every
  home by role.
- **Do nothing before 0.2.0:** rejected by the owner's direction; steps 1 to 3 change text and
  ETHOS's own tree only.

### 13. Order and cost

| Step | What                                                                                                                                                                       | Class                             | Product, tests | When                                                                                   |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------- | -------------------------------------------------------------------------------------- |
| 1    | this design, reviewed to one signed text; it stays active                                                                                                                  | no rule                           | 0, 0           | now                                                                                    |
| 2    | the text of decision 11's step 2                                                                                                                                           | ETHOS's own law                   | 0, 0           | one off-gate row, in a weekly batch whose slot is free                                 |
| 3    | ETHOS's tree: the plan divides; each open note, follow-up and withdrawn task is disposed once; the build tree is sorted                                                    | no rule; a few path constants     | about 3, 3     | off-gate rows, one to a free weekly batch, none after the freeze; the rest after 0.2.0 |
| 4    | native selection prefers a Change the lane created to one it inherited; readers: drafts by age, rows by state, research past review, decisions without a part, build homes | a narrowing; new code, no refusal | about 275, 400 | after 0.2.0, the `status` row and the test budget step                                 |
| 5    | the fleet: role homes, research fields and the parts of a decision as reporting obligations, with previews                                                                 | a new rule, reporting             | about 190, 230 | after 0.2.0, with DR-0027's                                                            |

The figures for steps 4 and 5 are the decidability seat's, within 40 percent, from measured commits
of similar shape; the reader of decision 10 adds about 80 and 120, from the decision-record checker
of similar shape. Step 4's first part is a narrowing, which the law freeze admits: it may take a
free off-gate slot once the test budget step has landed, and it otherwise lands with the rest of
step 4. A lane that has created none still attaches to a single inherited Change, as today; ending
that adds a refusal. Steps 4 and 5 do not fit the test ceiling's 247 free lines without the prepared
budget step. Step 3 keeps the plan's path, so its 23 tracked mentions stand; only links to anchors
among the moved lines change.

Step 5 moves repositories in this order: ETHOS; then the producers whose documents others cite;
then the guidance and benchmark repositories; then the two repositories under repair, inside
their repair lanes. A repository without a documentation home is asked for nothing, and a
repository with another maintainer moves only with that maintainer.

### 14. Review record

- **Revision 1**, commit `ae42de7cb`: a fourth object for intake, a `proposals` home, roadmap rows
  as a file, a documentation tier and direction paths.
- **Fleet seat on revision 1: approve with conditions.** Taken: mapping by file kind with a
  preview for each file, exemptions by role and by toolchain, the corrected census, the order of
  the fleet's moves, and no second intake in any repository.
- **Essence seat on revision 1: block.** The law that the design changed was not listed; role
  homes contradicted DR-0027 without an answer; the contract's three questions were unanswered;
  the dispositions were not the contract's. Taken: decisions 1, 3, 7, 8 and 11, and the end state
  as the contract's invariants.
- **Decidability seat on revision 1: block.** The documentation tier does not exist and is no
  narrowing; a class by a file's content is not decidable at admission; the claim that step 2
  changes no rule was false; two states read outside the tree. Taken: no tier and no path class;
  each change of law has its step; a state is read from one tree and a cut is a release.
- **Owner after revision 1:** no backlog; the review's unanimous final text decides the rest; the
  build tree is brought to one shape.
- **Revision 2**, commit `25a6925a4`: the intake and the `proposals` home removed.
- **Revision 3**, commit `4034f0c6c`: no new carrier.
- **Fleet seat on revision 3: signed with four additions**, measured on every governed
  repository's accepted branch on 2026-11-15: index and template documents and declared
  normative sources in decision 7, the disposal of the one backlog tree, the producers of build
  paths in decision 9, and the fleet's order in decision 13. All four are in this text.
- **Decidability seat on revision 3: block, with five replacements.** A draft is never the Change
  a proof selects, is archived only with a design and one checked task, and costs `--change` on
  every lane command until selection passes over inherited Changes; a row of two Changes and a
  waived row have their readings; an index, a root file and a document without a role are no gap
  of the role check; a work directory without a readable owner is unknown and never residue, and
  the build rules are an observation and no obligation; steps 2 to 4 have their slots. All five
  are in this text.
- **Owner after revision 3:** the first build cleanup may proceed; ETHOS and the governed
  repositories strengthen research, analysis, comparison, trade-offs, reasons and scope. Decision
  10 answers it.
- **Revision 4**, commit `8b2dec9ed`: the decidability seat's replacements and decision 10.
- **Input from a governed repository's session on decision 10**, counted on its 40 decisions:
  most rest on a measurement of their own and not on an outside source; a third name an
  alternative. Taken: the two kinds of source in decision 6, the named exclusions of
  `Applies to`, one study for a shared value, and a reader that lists and does not refuse.
- **Essence seat on revision 3: block, with five replacements.** The plan's rows are a release's
  execution plan and its release Change copies none; only the lines that describe the end state
  leave the plan, which keeps its eight batches; the role table answers the contract's three
  questions; a deferral's draft names its owner, its next action and the release at which it is
  read again; decision 9's rules get an owner and three more texts are listed. Its notes on the
  later revisions are taken as well: a leftover sentence removed, the three answers for decision
  10's form, the paradigm's row, the proposal's capability list, and the open settlement task.
  All are in this text.
- **Revision 5**, commit `78d74f4c2`, frozen for a confirmation round.
- **Confirmation round on revision 5.** The fleet seat signed with two replacements: no draft on
  a governed repository's accepted branch before step 4 unless every session names its Change,
  and decisions that the design numbers. The essence seat gave four: what OpenSpec's design
  instruction already asks, the scenario on an inherited Change among the law, this Change as
  active and not a draft, and the contract held at its bound. The decidability seat gave four:
  selection prefers a created Change and adds no refusal, what a decision and a part are for the
  reader, the topology's text only, and the plan keeping its path. All ten are in this text.
- **Revision 6**, commit `6f6165611`, is the text that every seat signed on 2026-11-15. Only this
  record was added after it.
  - "Fleet seat on revision 6: signed; a draft reaches a governed repository's accepted branch
    only after step 4 or with every lane command naming its Change, the reader finds bullet and
    heading decisions, and no rule reaches back to an archived design."
  - "Essence and contract: signed at 6f6165611. No carrier is added, each change of law this seat
    found is listed with its step, and the three questions are answered truthfully."
  - "Decidability seat: signed revision 6; each state and check is decided from one tree and its
    declarations; the readers of build homes and of a study's review date read one host and the
    day, and refuse nothing; the selection change concerns a lane before it merges its base and
    adds no refusal."
- **Readings the seats left for step 4's Change**, none blocking. The selection sentence of
  decision 3 holds for a lane that has not merged its base; after that merge the product already
  tells a lane's own Change from an inherited one. For a governed repository, "landed" in decision
  3's condition means in the release it runs. With "prefers", the scenario on an inherited Change
  stands and gains a case. While this design is the only open Change on a branch, a lane that
  creates none writes under it, which only the agent rule guards. The reader's definition of a
  decision makes "which the design numbers" unnecessary.

## Risks / Trade-offs

- **Drafts that pile up are a backlog by another name.** A draft costs a proposal that validates,
  the reader prints their count and the oldest age, and a rejected draft leaves by its archive.
- **Open Changes on the accepted branch.** A draft is open by rule; the reader keeps it apart from
  work so that an unfinished Change stays visible as one.
- **Role homes move files.** The fleet seat counted the mentions: 49 in ETHOS for three
  directories, and 715 in the two repositories under repair. The step reports first and moves a
  repository in its own lane.
- **Role homes move carried paths.** A move of a path that an installation carries is a
  release entry.
- **Cost before 0.2.0.** Steps 2 and 3 take off-gate slots that other rows wanted.

## Open Questions

- Which off-gate slots do steps 2 and 3 take, beside the gate record that holds the first?
- Are the 248 follow-ups and 96 withdrawn tasks disposed one by one, or only those that a current
  reader still needs?
