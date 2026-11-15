# Design

## Context

Measured on `dev` at `c79f3aaf8` and on 14 governed repositories of the releasing host on
2026-11-15; the three research pages of this Change hold the figures and the sources.

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
  names in 9 documentation homes, four forms of plan, four forms of contract, two of research.
- **Practice elsewhere** (primary sources, read 2026-11-15) agrees on five points. A proposal is
  one document with an identity and a state for "not now". Acceptance is not scheduling. The
  design document is a record, and execution is another object. Intake is apart from tracked
  work. A roadmap that is hand-kept in a file goes stale, so projects keep entries as thin
  pointers to tracked objects or generate the view from metadata. The sources disagree on a
  backlog: one method keeps none on purpose, most keep a holding place.
- **The owner decided two things on 2026-11-15**, after the first revision: there is no backlog,
  and the remaining choices of this design are settled by the review once every seat signs one
  text.

## Goals / Non-Goals

Goals:

- Everything that must outlive a session has one carrier in the repository, named by its nature,
  with an identity, states and a reader, and a price that fits it.
- ETHOS provides the carriers and their mechanisms once for every governed repository.
- A reader finds the end state, what is committed and in what order, what is proposed and the
  evidence behind each, from the tree alone.
- No state is written twice: what a tool can derive from the tree is derived.

Non-Goals:

- A backlog, an inbox or a feedback registry, in ETHOS or in a governed repository.
- A project-management system, estimates, assignees or boards.
- A carrier for conversation. A message becomes a draft, a row, a task or a decision, or it is
  not kept.
- A fixed tree of subjects. Subjects, their names and their number stay with each repository.
- A second place for task progress. OpenSpec Changes keep it.

## Decisions

### 1. Seven layers, sorted by what an object is

| Layer         | Says                                         | Lives until                 | Carrier                         |
| ------------- | -------------------------------------------- | --------------------------- | ------------------------------- |
| Contract      | what the product is and its end state        | the product changes meaning | contract documents              |
| Specification | what the product does now                    | the next accepted Change    | `openspec/specs`                |
| Decision      | why a choice was made                        | a successor replaces it     | decision records                |
| Direction     | where it goes, in what order, what is unsure | done, declined or replaced  | the roadmap and draft Changes   |
| Change        | one bounded step                             | its archive                 | `openspec/changes`              |
| Explanation   | how to use and understand it                 | its subject changes         | architecture, guides, reference |
| Evidence      | what was observed                            | its retention or review     | proofs, receipts, research      |

Direction is the layer the law lacked. The contract layer owns the end state and nothing about
order; the Change layer owns one step and nothing about the next.

### 2. Three direction objects and research

| Object    | Nature                                           | Identity          | Written                                  | Derived                                   |
| --------- | ------------------------------------------------ | ----------------- | ---------------------------------------- | ----------------------------------------- |
| End state | invariants as readings with today's value        | one document      | the sentence and its command             | each reading's value                      |
| Roadmap   | ordered rows, each a pointer to one Change       | the Change's name | release, batch, what it follows          | open, drafted, active, landed             |
| Draft     | an idea, a defect's repair or a design, proposed | the Change's name | a proposal, and a design when it has one | draft, by having no task; its age in cuts |
| Research  | dated findings about the world, with sources     | subject and slug  | active, settled, superseded; review date | due for review                            |

- **End state.** The contract family states each terminal invariant as a reading: the sentence,
  the command that reads it and the value today. It replaces the plan's completion boundary.
- **Roadmap.** Rows are data in one file for each release line. A row names its Change, its
  release and batch and the rows it follows. It holds no status: a row is landed when the Change is
  archived on the accepted branch, active when the Change has tasks, drafted when it has none, and
  open when no Change of that name exists. The view is printed by a reader and stored nowhere.
- **Draft.** OpenSpec has this object already: a Change without tasks validates strictly, and its
  list and view name it a draft (probed on 2026-11-15 with the installed 2.0.0). A draft holds a
  proposal: why, what would change, and the impact. A design that spans several Changes is a draft
  with a design document that lists its member Changes. There is no other carrier for intent that
  is not yet admitted, and no backlog: an idea that is worth keeping is a draft, and one that is
  not is let go.
- **A draft is disposed at the weekly cut** in one of the four ways the contract names. Accepted:
  it gains tasks and a roadmap row, or, for a design, a decision record and the rows of its
  members. Superseded or rejected: it is archived with one sentence that names the owner that
  covers it or the reason, so the archive keeps what the contract asks to keep. Pending
  verification: it stays a draft and names the missing fact. A draft older than two cuts is
  reported.
- **A design draft stays active while it is the current design.** It is edited as its members
  land, and it is archived when the last has landed and its lasting content is settled: the
  decision in a record, the order on the roadmap, the explanation in the architecture pages.
  This removes the defect of today's form, where a design freezes at its archive while it is still
  the current one.
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
| `roadmap`      | roadmap                      | `plans`, `future`, a root roadmap             |
| `research`     | research                     | `research`, `studies`                         |
| `architecture` | explanation of the structure | `architecture`, `concepts`                    |
| `guides`       | how-to and tutorial          | `guides`, `operations`, `start`, `experience` |
| `reference`    | reference                    | `reference`                                   |
| `history`      | retired rationale            | `history`, a directory of retired plans       |

`current` and `future` are states, which DR-0011 already refused as directories.

The fleet seat read every governed documentation home against this table (the census holds its
counts), and five rules follow from what it found:

- **A document maps by its kind, never by its directory's name.** One repository's `operations`
  holds runbooks beside a design of its architecture and its program of work; another's holds
  runbooks only. The repair preview names each file's target, and a directory of two kinds splits.
- **What carries no role is exempt by role or by toolchain.** Evidence under a documentation home
  is reported as belonging to the record root of DR-0027, with that repair. The taxonomy and
  generated views follow DR-0027's design. A home that another documentation toolchain builds is
  exempt until the documentation contract states how such a home declares a role.
- **A repository without a documentation home is asked for nothing.**
- **An asset sits beside the document that uses it, or under one asset name of its home.**
- **No governed repository keeps a backlog carrier.** The one that tracks a backlog tool's tree
  disposes each open task as a draft, a row or a closed item and retires the tree, in its own lane
  and after a report.

### 4. A price that fits: drafts and research

A draft's files and a research study are direction paths. Creating a draft needs no other Change,
which admission already grants to the files of a new Change. A write that touches only direction
paths takes the documentation tier of the proof: the documentation contract, OpenSpec validation,
Markdown, prose, links and secrets. It still needs a Work Lane, a signed commit and a landing, so
the accepted branch keeps one way in. A draft is told from a Change in work by the tree alone: it
has no task file. Roadmap rows, the end state, a decision record and a Change's first task alter
what is committed; they keep the full price.

A draft on a lane's pushed proposal ref is already durable and readable by every session of the
repository before it lands.

### 5. The law that changes

A rule that blocks the end state is replaced by its successor, and the successor says so.

| Text                                                           | Change                                                                    |
| -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `repository-governance`, requirement `Product Design Contract` | two authorities become the contract family, the roadmap and the drafts    |
| DR-0011, structure chosen by each repository                   | a successor: role homes fixed, subjects free, no empty carrier            |
| the documentation contract, portability boundary               | the role homes are part of the portable contract                          |
| DR-0016 and the task rule on follow-ups                        | a withdrawn task and a follow-up each name a draft or a roadmap row       |
| the convergence rule that every Change closes                  | a draft and a design draft stay open by rule, bounded by the cut's report |
| DR-0027's design, section 10, on `docs/plans`                  | `docs/plans` retires; its content divides by layer                        |

The plan's sentences against a backlog and a feedback registry stand, and this design keeps them.
DR-0012's sentence that leaves documentation subjects to each repository stands.

### 6. The session rule

The contract gains one sentence and the agent rules one procedure. The sentence: a session, an
agent's memory and an ignored directory are caches; only the repository carries what must last.
The procedure: at each safe boundary an agent asks what exists only in its session and writes it
to the carrier of its kind; a handoff is derived from the repository and never the reverse.

### 7. Tools

The tool study found no tool that meets the constraints and none that carries these objects as
plain text beside OpenSpec. The tracker that stores text fails with several writers: its
sequential identities collide across branches and then stop its own listing. The tracker that
merges well stores a database in ignored directories. The others have no 1.0 release. No tool is
a dependency of this design.

The one mature tool that fits is the one the fleet already runs. OpenSpec's maintainers give a
Change without tasks as their answer to requests for a backlog, and they name the risk of turning
OpenSpec into a project-management tool. The design takes that answer whole, and three practices
from the other tools: a roadmap whose state is read from the tree and where a mark written by
hand has no authority; an identity that two branches cannot both allocate, which a Change's name
is; and a review instant on a research record.

### 8. Order: ETHOS first, report before refusal

1. This Change: the design, its review by three seats to one signed text.
2. The law for ETHOS: the successor of DR-0011, the specification delta and the contract's
   sentence.
3. ETHOS's own tree: the roadmap rows as data; each open note, follow-up and withdrawn task
   disposed once as a draft, a row, a task of an open Change or a closed item; the terminal plan
   divided; `docs/plans` retired.
4. The documentation tier for direction paths. This narrows a refusal.
5. Readers: `status` prints rows left and drafts by age; the weekly page reads them.
6. The fleet: a report of first-level names outside the role homes, with the preview of its
   repair for each file. It enters as a reporting obligation and refuses nothing before a later
   release. Repositories move in this order: ETHOS; then those whose documents others cite; then
   the rest; a repository under repair inside its repair lane; a repository with another
   maintainer only with that maintainer.

Steps 2 and 3 change no rule for a governed repository. Step 6 is a new rule and waits for the
rule row after 0.2.0.

### 9. Review record

Three seats review the design; this section holds each verdict and what the design took from it.

- **Revision 1**, commit `ae42de7cb`, had a fourth direction object, an intake of short files
  under its own home, and a `proposals` home.
- **Fleet seat on revision 1, 2026-11-15: approve with conditions, no blocker.** Its conditions
  are in the text above: a mapping by file kind with a preview for each file, exemptions by role
  and by toolchain, the corrected census, and the order of the fleet's moves. Its condition of
  one intake for each repository became the rule that no repository keeps a backlog carrier.
- **Owner, 2026-11-15, after revision 1:** no backlog; the review's unanimous final text decides
  the rest.
- **Revision 2** is this text: the intake and the `proposals` home are gone, and a draft Change
  carries intent that is not yet admitted.

## Risks / Trade-offs

- **Drafts that pile up are a backlog by another name.** The cut disposes every draft or reports
  it, the weekly page prints their count and the oldest age, and a declined draft leaves the open
  set by its archive.
- **A third authority.** The specification allowed two on purpose, after a period of parallel
  plans. The answer is one owner for each proposition: the row list owns order, a draft owns one
  proposal, and neither restates the other.
- **Active Changes that stay open.** The fleet's rule so far is to close every Change. A design
  draft is open by rule until its members land; the reader that lists drafts by age keeps it
  visible.
- **Role homes against truthful structure.** DR-0011 feared empty and misleading carriers. No
  role, no directory; and a role home holds the repository's own subjects.
- **Cost before 0.2.0.** Steps 2 and 3 are off-gate rows and the owner allowed one a week. They
  ride with a batch's proof or wait.
- **Moved paths.** Documents that an installation carries keep their paths in steps 2 and 3. A
  later move of a carried path is a release entry.

## Open Questions

- Is `contract` the right name for the home that four repositories call `governance`?
- Are the 248 follow-ups and 96 withdrawn tasks disposed one by one, or only those that a current
  reader still needs?
- Does the first task of a Change, written into a draft, need the full proof, or only the first
  commit that changes a path outside the Change?
