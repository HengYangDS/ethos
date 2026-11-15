# Proposal

## Why

A repository's future has no designed carrier. The owner stated the rule on 2026-11-15: a session is
volatile and the repository is stable, so what matters is kept in the repository, in the best
place and carrier for its kind; the common law and mechanisms come from ETHOS and not from each
repository's own choice; and a decision record that contradicts the end state is replaced.

The current law gives the future one document. The `repository-governance` specification keeps
"exactly two canonical design authorities", the product design contract and the terminal plan,
and the plan forbids a backlog and a feedback registry. Both documents hold 500 nonblank lines of
the 500 a document may hold. What does not fit went elsewhere, measured on `dev` at `c79f3aaf8`:

- 248 follow-up bullets in 152 of 353 archived Changes, and 96 tasks withdrawn "until taken up";
- 174 archived Changes that change no requirement and exist to carry a design or a record;
- the 43 rows of the release-candidate gate in a decision record's prose and an untracked script;
- one session's untracked notes with 38 sections of defects, rulings and proposals, 12 of them
  written in one day, and 75 files of agent memory;
- no document in the `planned` or `experimental` state, although the vocabulary has both.

The fleet shows the second half. DR-0011 made document metadata portable and left the physical
structure to each repository. Of 14 governed repositories on the releasing host, 9 have a
documentation home with 20 different names at its first level, five forms of a roadmap or plan
(nine repositories have none), five forms of a contract or end-state document (eight have none)
and two forms of research.

One cause runs under both. Every tracked write costs a Work Lane, a Change and a proof, whether
it is a kernel change or one sentence of an idea. A carrier whose price does not fit its object is
not used, so ideas moved to carriers that cost nothing and keep nothing.

## What Changes

- The design names **direction** as a layer of its own between the contract and the Change, with
  four objects: the end state, the roadmap, the intake and the proposal. Research stands beside it
  as the dated evidence that proposals and decisions cite.
- Each object gets one home under the documentation home, named by its role, with an identity,
  states and a reader. The first level of a documentation home names roles, which ETHOS fixes for
  every governed repository; below it each repository keeps its own subjects. No role means no
  directory.
- A roadmap row is a pointer to a Change by name, and its state is derived from the Change's
  directory and never written by hand.
- A write to a direction path needs no Change and takes the documentation tier of the proof, so
  the price of recording an idea fits the idea.
- The law that stands in the way is replaced and not routed around: the two-authority requirement,
  the plan's sentences on backlogs, DR-0011's choice of structure by each repository, and the
  matching sentence of DR-0012.
- ETHOS applies all of it to its own tree first: the terminal plan divides into its end state, its
  architecture pages and its roadmap; `docs/plans` retires; the gate's rows, the pending notes and
  the open follow-ups move to their carriers.

This Change carries the design and its review. The specification deltas, the decision record and
the moves arrive in the member Changes that the design lists, each with its own proof.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None in this Change, so `skip_specs: true` applies. The member Changes modify
`repository-governance` (the requirement `Product Design Contract`) and `repository-paradigm` (the
documentation home).

## Impact

This Change: its own documents and two research pages under `docs/research/direction-carriers/`.
The member Changes: `docs/` of ETHOS, the documentation contract, the paradigm declaration, the
write admission and the status reader, then each governed repository in its own lane. No governed
repository is refused by a rule of this design before a release has reported it.
