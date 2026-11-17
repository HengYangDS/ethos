# Design

## Context

See the [proposal](proposal.md) and
DR-0031, the decision record that task 1.2 of this Change writes. DR-0028 took the previous test
step the same way. Every figure below was read on 2026-11-17: the ceilings from the report of the
source-budget gate, and each module's delta with the budget tool on this Change's tree.

## Goals / Non-Goals

Goals:

- One reviewed 5,000 step for the tests, with its removals and its consumers recorded.

Non-Goals:

- A product or tools step. The product stands at 82,822 of 85,000 and the tools at 8,908 of
  10,000.
- Compressing or relabeling tests, merging tests that assert distinct obligations, and the
  structural reduction that DR-0019 assigned to 0.3.0.
- A review by coverage of each test. DR-0031 gives it to the next review.
- The work of the rows of 0.2.0-beta.13.

## Decisions

1. **Two removals land with the step.**
   - **Rests on:** the budget tool's delta for each module against the batch's head: the support
     module of the command runner -4.0 and the tests of the hosted tool supply -8.9; a search of
     the whole tree, which finds each helper's name once, at its definition.
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
3. **The need is measured where a slice is built and estimated elsewhere.**
   - **Rests on:** the preparation reports of two first slices, 181.0 and 150.0; the estimates of
     six design studies, 1,210 to 1,400 together; and the ten sized Changes of 0.2.0-beta.11,
     which measured 2.1 times their estimates on their prepared stack.
   - **Considered:** applying that factor to the six estimates, which gives about 2,540 to 2,940.
   - **Chosen because:** these estimates come from studies that measured a spike or a sibling
     module, where the earlier ones came from the plan alone. The factor stays a risk below and is
     no part of the figure.
   - **Applies to:** the expectation of about 1,540 to 1,730 for the first slices. It is no budget
     for any row.
4. **One step of 5,000, alone and first.**
   - **Rests on:** DR-0010's rule of one reviewed step, and DR-0028's finding on a step inside a
     row.
   - **Considered:** the step inside the first slice that needs it; two steps at once.
   - **Chosen because:** a step inside a row puts the budget decision in that row and leaves the
     others without space, and DR-0010 allows one step for each review.
   - **Applies to:** the test ceiling only, from 110,000 to 115,000.

## Risks / Trade-offs

- The space is shared: a slice that overruns its estimate takes from the others. DR-0031 names the
  revisit point at 113,000.
- If the six estimates run at the factor that 0.2.0-beta.11 measured, the first slices need about
  2,900 to 3,300, which the step still holds.
- The step is not expected to hold the release candidate: the remainders of these rows and the
  rows of the later batches follow.
- The census reads syntax trees. It cannot see two tests that assert one behavior in different
  words.
