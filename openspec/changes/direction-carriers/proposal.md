# Proposal

## Why

A repository's future has no designed carrier. The owner stated the rule on 2026-11-15: a session is
volatile and the repository is stable, so what matters is kept in the repository, in the best
place and carrier for its kind; the common law and mechanisms come from ETHOS and not from each
repository's own choice; and a decision record that contradicts the end state is replaced.

The current law gives the future one document. The `repository-governance` specification keeps
"exactly two canonical design authorities", the product design contract and the terminal plan, and
the plan forbids a backlog and a feedback registry. Both documents hold 500 nonblank lines, the
default bound; the repository's bound is 560 until the command reference splits. What does not fit
went elsewhere, measured on `dev` at `c79f3aaf8`:

- 248 follow-up bullets in 152 of 353 archived Changes, and 96 tasks withdrawn "until taken up";
- 174 archived Changes that change no requirement and exist to carry a design or a record;
- the rows of the release-candidate gate in a decision record's prose and an untracked script;
- one session's untracked notes with 38 sections of defects, rulings and proposals, 12 of them
  written in one day, and 75 files of agent memory;
- no document in the `planned` or `experimental` state, although the vocabulary has both.

The fleet shows the second half. DR-0011 made document metadata portable and left the physical
structure to each repository. Of 14 governed repositories on the releasing host, 9 have a
documentation home with 20 different names at its first level, four live forms of a roadmap or plan
(ten repositories have no live one), four forms of a contract or end-state document (ten have none)
and two forms of research.

One cause runs under both. Every tracked write costs a Work Lane, a Change and a proof, whether
it is a kernel change or one sentence of an idea. A carrier whose price does not fit its object is
not used, so ideas moved to carriers that cost nothing and keep nothing.

## What Changes

Revision 1 of the design proposed new carriers. The review and the contract's own test for a new
carrier refused them, and the owner decided against a backlog. The design that stands adds none.

- Intent that is not yet admitted is an OpenSpec draft, a Change without tasks. A draft may stay
  open, is disposed in the contract's four ways, and a design that spans Changes stays an active
  draft while it is the current design. A deferral creates its draft. There is no backlog.
- The roadmap is the terminal plan and a derived view. The plan divides by lifetime, keeps the
  order and gains the gate's rows by name; a row's state is read from the tree.
- The end state is the contract's invariants, each with the command that reads it.
- Research is built as a role, with a review date.
- A decision shows its reasoning in four parts that a reader can list: what it rests on, what
  was considered, why it was chosen with the trade-off it accepts, and where it applies.
- The first level of a documentation home names a document role, with names that ETHOS fixes for
  every governed repository; below it each repository keeps its own subjects.
- One sentence states that a session, an agent's memory and an ignored directory authorize
  nothing, and the build tree gets its rule: nothing there is the only copy of what must last.
- The law that stands in the way is replaced sentence by sentence, each with the step that
  carries its reader; most of the standing law stands.

This Change carries the design and its review and stays an active draft while it is the current
design. The text, the moves and the readers arrive in the member Changes that the design lists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None in this Change, so `skip_specs: true` applies. The member Changes modify
`repository-governance` (the scenarios on product extension roots and on an adopter's roots) and
`repository-paradigm` (the role-to-name table and the reporting obligations). The requirement
`Product Design Contract` stands.

## Impact

This Change: its own documents and three research pages under `docs/research/direction-carriers/`.
The member Changes: the contract's and the plan's text, ETHOS's documentation and build trees, the
readers, and then each governed repository in its own lane. No governed repository is refused by
a rule of this design before a release has reported it.
