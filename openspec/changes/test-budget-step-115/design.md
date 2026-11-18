# Design

## Context

See the [proposal](proposal.md) and
DR-0033, the decision record that task 1.2 of this Change writes. DR-0028 took the previous test
step the same way. The ceilings and the census were read on 2026-11-19 at the head of the lane
that follows 0.2.0-beta.11; each helper's delta and each slice's size were measured with the
budget tool on 2026-11-17.

## Goals / Non-Goals

Goals:

- One reviewed 5,000 step for the tests, with its removals and its consumers recorded.

Non-Goals:

- A product or tools step. The product stands at 82,985 of 85,000 and the tools at 8,908 of
  10,000.
- Compressing or relabeling tests, merging tests that assert distinct obligations, and the
  structural reduction that DR-0019 assigned to 0.3.0.
- A review by coverage of each test. DR-0033 gives it to the next review.
- The work of the rows that the space is for.

## Decisions

1. **Two removals land with the step.**
   - **Rests on:** the budget tool's delta for each module: the support module of the command
     runner -4.0 and the tests of the hosted tool supply -8.9; a search of the whole tree at the
     lane's head, which finds each helper's name once, at its definition.
   - **Considered:** landing the step without them, since 12.9 is a quarter of a percent of the
     step.
   - **Chosen because:** DR-0010 allows a step only after the growing owner retires what is
     proved unused, and the owner's rule asks for the removal first.
   - **Applies to:** the two modules. It drops no test and no named scenario.
2. **A helper that only a child process calls stays.**
   - **Rests on:** the same search: the helper that pauses after an effect is named in two
     support modules inside text that a test passes to a child interpreter.
   - **Considered:** counting it as unused, as a reader of syntax trees does.
   - **Chosen because:** removing it breaks the tests of interrupted effects.
   - **Applies to:** the census's figure, which is two helpers and not three.
3. **The need is stated only where a slice is built and measured.**
   - **Rests on:** the preparation reports of four built first slices: 449.3, 181.0, 150.0 and
     696.3, together 1,476.5 against 516 free after the removal.
   - **Considered:** adding the estimates of the rows that are not built. The ten sized Changes
     of 0.2.0-beta.11 measured 2.1 times their estimates on their prepared stack.
   - **Chosen because:** the measured slices alone are nearly three times the free space, so the
     step's necessity does not rest on an estimate.
   - **Applies to:** the figure in DR-0033. It is no budget for any row, and each slice is
     measured again when it enters the lane.
4. **One step of 5,000, alone and first.**
   - **Rests on:** DR-0010's rule of one reviewed step, and DR-0028's finding on a step inside a
     row.
   - **Considered:** the step inside the first slice that needs it; two steps at once.
   - **Chosen because:** a step inside a row puts the budget decision in that row and leaves the
     others without space, and DR-0010 allows one step for each review.
   - **Applies to:** the test ceiling only, from 110,000 to 115,000.

## Risks / Trade-offs

- The space is shared: a slice that grows in the lane takes from the others. DR-0033 names the
  revisit point at 113,000.
- The four slices were measured against the tree of 2026-11-17. A slice that has to be rebuilt on
  today's tree may measure more; the step leaves about 4,000 beyond them.
- The step is not expected to hold the release candidate: the remainders of these rows and the
  rows of the later batches follow.
- The census reads syntax trees. It cannot see two tests that assert one behavior in different
  words.
