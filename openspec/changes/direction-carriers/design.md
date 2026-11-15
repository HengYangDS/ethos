# Design

## Context

Measured on `dev` at `c79f3aaf8` and on 14 governed repositories of the releasing host on
2026-11-15; the two research pages of this Change hold the figures and the sources.

- **One carrier for the future, and it is full.** The specification keeps exactly two design
  authorities. The terminal plan holds the end state's architecture, the convergence order and the
  rules of convergence in one document of 500 nonblank lines, the bound. The contract holds 500.
- **Intent leaves by the side doors.** 248 follow-up bullets and 96 withdrawn tasks sit in archived
  Changes, which the specification says own no queue. 174 of 353 archived Changes change no
  requirement; the largest of them are designs that span many later Changes, and an archive is
  immutable while such a design is still the current one. The gate's 43 rows are prose in a
  decision record and a list in an untracked script. Defects, rulings and proposals of a week sit
  in one session's untracked notes and in agent memory.
- **A session is not a carrier.** On 2026-11-15 a request failed and a session lost two hours and
  seventeen minutes. What was in files, detached processes and pushed refs was intact. What the
  session alone held was gone.
- **One price for every write.** A tracked write needs a Work Lane, a Change and a proof. That is
  right for a change of behavior and wrong for a sentence of intent, so the sentence is not
  written where it would last.
- **No common shape.** DR-0011 fixed metadata and left structure to each repository: 20 first-level
  names in 9 documentation homes, five forms of plan, five forms of contract, two of research.
- **Practice elsewhere** (primary sources, read 2026-11-15) agrees on five points. A proposal is
  one document with an identity and a state for "not now". Acceptance is not scheduling. The
  design document is a record, and execution is another object. Intake is apart from tracked
  work. A roadmap that is hand-kept in a file goes stale, so projects keep entries as thin
  pointers to tracked objects or generate the view from metadata. The sources disagree on a
  backlog: one method keeps none on purpose, most keep a bounded holding place.

## Goals / Non-Goals

Goals:

- Everything that must outlive a session has one carrier in the repository, named by its nature,
  with an identity, states and a reader, and a price that fits it.
- ETHOS provides the carriers and their mechanisms once for every governed repository.
- A reader finds the end state, what is committed and in what order, what is proposed, what is
  only an idea, and the evidence behind each, from the tree alone.
- No state is written twice: what a tool can derive from the tree is derived.

Non-Goals:

- A project-management system, estimates, assignees or boards.
- A carrier for conversation. A message becomes an item, a proposal or a decision, or it is not
  kept.
- A fixed tree of subjects. Subjects, their names and their number stay with each repository.
- A second place for task progress. OpenSpec Changes keep it.

## Decisions

### 1. Seven layers, sorted by what an object is

| Layer         | Says                                         | Lives until                 | Carrier                         |
| ------------- | -------------------------------------------- | --------------------------- | ------------------------------- |
| Contract      | what the product is and its end state        | the product changes meaning | contract documents              |
| Specification | what the product does now                    | the next accepted Change    | `openspec/specs`                |
| Decision      | why a choice was made                        | a successor replaces it     | decision records                |
| Direction     | where it goes, in what order, what is unsure | done, declined or replaced  | roadmap, intake, proposals      |
| Change        | one bounded step                             | its archive                 | `openspec/changes`              |
| Explanation   | how to use and understand it                 | its subject changes         | architecture, guides, reference |
| Evidence      | what was observed                            | its retention or review     | proofs, receipts, research      |

Direction is the layer the law lacked. The contract layer owns the end state and nothing about
order; the Change layer owns one step and nothing about the next.

### 2. Four direction objects and research

| Object    | Nature                                          | Identity                | Written states                                          | Derived                                |
| --------- | ----------------------------------------------- | ----------------------- | ------------------------------------------------------- | -------------------------------------- |
| End state | invariants as readings with today's value       | one document            | none                                                    | each reading, by its command           |
| Roadmap   | ordered rows, each a pointer to one Change      | the Change's name       | release, batch, what it follows                         | open, active, landed                   |
| Intake    | one idea, defect, improvement, refactor or wish | date and slug, one file | open, unverified                                        | age in cuts                            |
| Proposal  | a design that spans Changes or is not admitted  | slug, one file          | draft, review, accepted, deferred, declined, superseded | implemented, when its rows have landed |
| Research  | dated findings about the world, with sources    | subject and slug        | active, settled, superseded; a review date              | due for review                         |

- **End state.** The contract family states each terminal invariant as a reading: the sentence,
  the command that reads it and the value today. It replaces the plan's completion boundary.
- **Roadmap.** Rows are data in one file for each release line. A row names its Change, its
  release and batch and the rows it follows. It holds no status: a row is landed when the Change is
  archived on the accepted branch, active when the Change directory exists there or on a proposal
  ref, and open otherwise. The view is printed by a reader and stored nowhere.
- **Intake.** One short file for each item: what was seen, where, by whom, what it would change.
  An item is disposed at a weekly cut in exactly one of the four ways the contract already names:
  accepted (it becomes a row, a proposal or a task of an open Change), superseded (it names the
  owner that covers it), pending verification (it stays, as `unverified`, and names the missing
  fact) or rejected (the cut's Change records the reason). A disposed item leaves the tree in the
  commit that disposes it. The tree therefore holds only open and unverified items, and an item
  older than two cuts is reported.
- **Proposal.** One document for a design that more than one Change will realize, or that no
  Change has admitted. It carries the fixed sections that the sources share: context, goals and
  non-goals, the design, alternatives considered, open questions, and the rows it would add.
  Acceptance writes a decision record and roadmap rows; it schedules nothing by itself. A
  proposal ends by being settled: its decision in a record, its rows on the roadmap and its
  explanation in the architecture pages. Then it leaves the tree.
- **Research.** A study states its question, the date and URL of each source, findings apart
  from inference, what it could not reach, what it informs and the date by which it is reviewed.
  A study that a decision cites is settled and is not edited; a newer study supersedes it.

The execution plan of a release needs no new object: it is the release's Change, opened at the
cut with the rows of its batch as its tasks.

### 3. Role homes: one name for one role in every governed repository

The first level of a documentation home names a role, and ETHOS fixes the names. The second level
names the repository's own subjects. A repository without a role has no directory for it.

| Home           | Role                         | Measured names that map to it                 |
| -------------- | ---------------------------- | --------------------------------------------- |
| `contract`     | contract and end state       | `governance`, a root contract or charter      |
| `decisions`    | decision                     | `decisions`                                   |
| `roadmap`      | roadmap                      | `plans`, `planning`, `future`, a root roadmap |
| `intake`       | intake                       | none in a documentation home                  |
| `proposals`    | proposal                     | none; designs sit in archived Changes         |
| `research`     | research                     | `research`, `studies`                         |
| `architecture` | explanation of the structure | `architecture`, `concepts`                    |
| `guides`       | how-to and tutorial          | `guides`, `operations`, `start`, `experience` |
| `reference`    | reference                    | `reference`                                   |
| `history`      | retired rationale            | `history`                                     |

`current` and `future` are states, which DR-0011 already refused as directories.

The fleet seat read every governed documentation home against this table (the census holds its
counts), and four rules follow from what it found:

- **A document maps by its kind, never by its directory's name.** One repository's `operations`
  holds runbooks beside a design of its architecture and its program of work; another's holds
  runbooks only. The repair preview names each file's target, and a directory of two kinds splits.
  A directory of retired plans is `history`.
- **What carries no role is exempt by role or by toolchain.** Evidence under a documentation home
  is reported as belonging to the record root of DR-0027, with that repair. The taxonomy and
  generated views follow DR-0027's design. A home that another documentation toolchain builds is
  exempt until the documentation contract states how such a home declares a role.
- **A repository without a documentation home is asked for nothing.**
- **An asset sits beside the document that uses it, or under one asset name of its home.**

### 4. A price that fits: direction paths

Intake items, research studies and proposals in `draft` are direction paths. A write that touches
only direction paths needs no Change, and its proof is the documentation tier: the documentation
contract, Markdown, prose, links and secrets. It still needs a Work Lane, a signed commit and a
landing, so the accepted branch keeps one way in. Roadmap rows, the end state, a proposal's
acceptance and a decision record change what is committed; they keep the full price.

One verb then records an item from any worktree in seconds and leaves it on a ref that every
session of the repository reads. Its form is decided in the member Change that builds it, after
the tool study.

### 5. The law that changes

A rule that blocks the end state is replaced by its successor, and the successor says so.

| Text                                                           | Change                                                                     |
| -------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `repository-governance`, requirement `Product Design Contract` | two authorities become the contract family and the direction carriers      |
| the terminal plan, on backlogs and a feedback registry         | the intake is that registry, bounded by the cut                            |
| DR-0011, structure chosen by each repository                   | a successor: role homes fixed, subjects free, no empty carrier             |
| the documentation contract, portability boundary               | the role homes are part of the portable contract                           |
| DR-0016 and the task rule on follow-ups                        | a withdrawn task and a follow-up each name an intake item or a roadmap row |
| DR-0027's design, section 10, on `docs/plans`                  | `docs/plans` retires; its content divides by layer                         |

DR-0012's sentence that leaves documentation subjects to each repository stands.

### 6. The session rule

The contract gains one sentence and the agent rules one procedure. The sentence: a session, an
agent's memory and an ignored directory are caches; only the repository carries what must last.
The procedure: at each safe boundary an agent asks what exists only in its session and writes it
to the carrier of its kind; a handoff is derived from the repository and never the reverse.

### 7. Tools

The carriers are plain text that reads and diffs without a tool, on two forges. A tool is taken
only where it keeps that and adds a reader or a safe writer. The second research page compares
the candidates; no tool is a dependency of this design.

### 8. Order: ETHOS first, report before refusal

1. This Change: the design, its review by three seats and the owner's decisions.
2. The law for ETHOS: the successor of DR-0011, the specification delta and the contract's
   sentence.
3. ETHOS's own tree: the roadmap rows as data, the intake seeded from the open notes and
   follow-ups with each one disposed, the terminal plan divided, `docs/plans` retired.
4. Direction paths in write admission and the documentation tier. This narrows a refusal.
5. Readers: `status` prints rows left and open items; the weekly page reads them.
6. The fleet: a report of first-level names outside the role homes, with the preview of its
   repair for each file. It enters as a reporting obligation and refuses nothing before a later
   release. Repositories move in this order: ETHOS; then those whose documents others cite; then
   the rest; a repository under repair inside its repair lane; a repository with another
   maintainer only with that maintainer.

Steps 2 and 3 change no rule for a governed repository. Step 6 is a new rule and waits for the
rule row after 0.2.0.

### 9. Review record

Revision 1 is commit `ae42de7cb`. Three seats review it; this section holds each verdict and what
the design took from it.

- **Fleet seat, 2026-11-15: approve with conditions, no blocker.** Its five conditions are in
  the text above: a mapping by file kind with a preview for each file, exemptions by role and by
  toolchain, one intake for each repository, the corrected census, and the order of the fleet's
  moves. The first two hold before the member Change of step 6 is written.

## Risks / Trade-offs

- **A third and fourth authority.** The specification allowed two on purpose, after a period of
  parallel plans. The answer is one owner for each proposition: the row list owns order, the
  intake owns what is undecided, and neither restates the other.
- **An intake that only grows.** A backlog decays into a list nobody reads. The cut disposes every
  item or reports it, and the weekly page prints the count and the oldest age.
- **Role homes against truthful structure.** DR-0011 feared empty and misleading carriers. No
  role, no directory; and a role home holds the repository's own subjects.
- **Cost before 0.2.0.** Steps 2 and 3 are off-gate rows and the owner allowed one a week. They
  ride with a batch's proof or wait; the owner decides.
- **Moved paths.** Documents that an installation carries keep their paths in steps 2 and 3. A
  later move of a carried path is a release entry.

## Open Questions

- Does the intake live in the documentation home on the accepted branch, on a dedicated ref, or in
  a tool's store? The design above assumes the first; the tool study may change it. Either way a
  repository has one intake: the Change that builds the verb states what becomes of the backlog
  tool's tree that one governed repository tracks today.
- Is `contract` the right name for the home that four repositories call `governance`?
- Do the 248 follow-ups and 96 withdrawn tasks enter the intake one by one, or only those that a
  current reader still needs?
