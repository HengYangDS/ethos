# Design

## Context

See [proposal.md](proposal.md). `ethos publish --retire` already deletes a proposal by exact
peer-local CAS once fresh observations show that the peer's accepted branch preserves its tip and no
review of it is open (`src/ethos/adapters/mutation/publication/retirement.py`). Only an operator who
remembers it starts it.

## Goals / Non-Goals

**Goals:**

- The publication that lets a peer retire a proposal names that retirement as its next action.
- A listing that cannot be read is reported, never read as "nothing to retire".

**Non-Goals:**

- Deleting proposals inside the accepted push. One request would mix a deletion with an update,
  which `publication_mixed_retirement_projection` refuses, and the deletion would precede the peer's
  accepted branch containing the tip, which proposal absorption requires first.
- A status view of leftovers from earlier publications; it can follow from the publication
  Attestations if leftovers still occur.

## Decisions

- **List only peers whose accepted branch moved.** Each gets one bounded `git ls-remote` of the
  role policy's proposal namespace after the push; a peer that only received a tag or a proposal is
  not read.
- **Judge preservation with `accepted_contribution`.** Retirement admission uses it, so a refreshed
  or repaired tip counts exactly when retirement would accept it, and patch equivalence never does.
- **Name the existing probe.** The next action is `ethos publish --retire` for the listed refs and
  peers; its own admission repeats every observation, so the listing grants nothing.

## Risks / Trade-offs

- [One more network read after each accepted publication] → It is bounded by the repository's
  `timeout.git_seconds`, and its failure only names the peer as unobserved.
