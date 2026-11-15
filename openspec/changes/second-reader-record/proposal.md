# Proposal

## Why

Three practices of the release work ask for a reader other than the author. DR-0029 names two,
the copies run before a tag and the weekly page. The third is a model review of each batch's diff
before its proof, which the owner authorized on 2026-11-10 and which the research page on
verification lists among the complementary reviews. No result that the product reads says that
any of the three took place, and the third had no carrier in the repository at all.

- The review lapsed. It was not run for the last landing of 0.2.0-beta.10 or for the five
  landings of 0.2.0-beta.11, because no step asked for it.
- Run late, on 2026-11-15, over that release's whole diff of product, tools and configuration (83
  files, 5.7 million tokens in two passes), it returned 13 leads. Four full proofs, the hosted
  runs of both forges and the copies run on 13 trees had passed the same code. The repair Changes
  of that release state, for each lead, the regression that decided it.
- Two of the leads were checks that the diff itself had loosened: an assertion of one queue
  record that became two, and an exact list of planned files that became a superset. No gate
  reads a weakened check.
- A second reading of the repairs' own diff (11 files, 1.0 million tokens) returned five more
  comments, each taken at least in part.

## What Changes

Candidates for a design; none is decided.

- A reading by someone other than the author is a record: its subject as an exact range or head,
  the reader, what was read and what was not, and a verdict for each finding. A reading that
  ended partial says so; an exit status or a count of findings is no coverage.
- One carrier for that record. To compare: evidence that a proof names, so that a landing's
  preview can state that no reading covers the head's code; a line of the release entry, which
  holds counts alone; the review of the proposal ref on a forge, which a repository without a
  forge lacks. Which of them survives a retired lane, which a repository without a model can
  produce, and what a batch costs decide the choice.
- It reports before it refuses, and it adds no required gap before 0.2.0.
- The reading's rules are data of the repository. One of them asks for every check that the diff
  makes less strict, with what it accepted before and after.
- The product names no model, endpoint or credential. A governed repository opts in.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

None while it is a draft. The release lead's lane tools hold the practice until then: a lane
with code is not proven without a complete reading and a verdict for each of its comments.

Owner: the release lead. Next action: compare the three carriers in a design, with the cost of
the readings of 2026-11. Read again: at the cut of 0.2.0-beta.13.
