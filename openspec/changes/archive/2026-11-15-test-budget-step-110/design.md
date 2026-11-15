# Design

## Context

See the [proposal](proposal.md) and
[DR-0028](../../../../docs/decisions/dr-0028-test-budget-step-110.md). DR-0023 took the previous test
step the same way. Every figure below was read on 2026-11-15: the ceilings from the report of the
source-budget gate, and each module's delta with the budget tool on this Change's tree.

## Goals / Non-Goals

Goals:

- One reviewed 5,000 step for the tests, with its removals and its consumers recorded.

Non-Goals:

- A product or tools step. The product stands at 81,263 of 85,000 and the tools at 8,622 of
  10,000.
- Compressing or relabeling tests, merging tests that assert distinct obligations, and the
  structural reduction that DR-0019 assigned to 0.3.0.
- The work of the rows of 0.2.0-beta.12.

## Decisions

1. **Four removals land with the step.**
   - **Rests on:** the budget tool's delta for each module against the landed tree: the host
     proof tests -29.2, the exit table tests -13.0, the rollback journey -5.8 and the host command
     tests -3.2; and the four modules' 60 tests, which pass after the removal.
   - **Considered:** landing the step without them, since 51.1 is one percent of the step.
   - **Chosen because:** DR-0010 allows a step only after the growing owner retires proved
     duplication, and each removal replaces copies by one shared run, read or helper.
   - **Applies to:** the four modules. It drops no named scenario.
2. **Two prepared removals are not counted.**
   - **Rests on:** a check of the prepared patch against the landed tree: the admission tests'
     hunks conflict with three commits that landed, and the lane repair tests' hunks remove a
     test that the tree does not hold.
   - **Considered:** reworking the admission removal of 7.0 now.
   - **Chosen because:** the host row of this batch rewrites the admission tests, so a rework
     here would be written twice; and the adopter bump as now prepared holds one table and one
     journey where its first preparation repeated a test.
   - **Applies to:** the figure in DR-0028, which is 51.1 and not the 84.3 of the first
     preparation.
3. **The need is measured where a row is prepared and estimated elsewhere.**
   - **Rests on:** the preparation reports of three rows, 351.9, 204.7 and 375.5; the plan's
     estimates for the other six, 670 together; and the ten sized Changes of 0.2.0-beta.11, which
     measured 1,662 against 785 estimated on their prepared stack.
   - **Considered:** the plan's estimates alone, which give 670 for the six rows that are not
     prepared and already exceed the 296 that remain after the removals.
   - **Chosen because:** the estimates left out refusal cases and journeys that the done
     conditions name, and the measured factor of 2.1 is the only reading of that omission.
   - **Applies to:** the expectation of about 2,340 for the batch. It is no budget for any row.
4. **One step of 5,000, alone and first.**
   - **Rests on:** DR-0010's rule of one reviewed step, and DR-0029's order.
   - **Considered:** the step inside the first row that needs it; two steps at once.
   - **Chosen because:** a step inside a row puts the budget decision in that row and leaves the
     others without space, and DR-0010 allows one step for each review.
   - **Applies to:** the test ceiling only, from 105,000 to 110,000.

## Risks / Trade-offs

- The space is shared: a row that overruns its estimate takes from the others. DR-0028 names the
  revisit point at 108,000.
- The step is not expected to hold the release candidate: 24 rows follow this batch.
- The three rows' sizes are measured on their prepared patches. One is being reworked after the
  lead's rulings and will move.
