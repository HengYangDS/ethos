# Design

## Context

DR-0026 is the tracked record of the release candidate's gate. The committee's resolution of
2026-11-14 changes the gate's dates and adds one item, and its text is a local document. The
owner's reading of the successor's whole text was due by the cut of 2026-11-19. The owner read it
and approved it as drafted on 2026-11-15.

## Goals / Non-Goals

Goals:

- The tracked tree holds the gate as the committee and the owner changed it.

Non-Goals:

- Changing a requirement, a rule or a date beyond the record's text.
- Editing DR-0026. The successor names it and leaves it as accepted.
- The commands of the weekly measures. The record says which values are still written by hand.

## Decisions

1. **The record lands with the approved text, less two code spans in one sentence.**
   - **Rests on:** the owner's answer of 2026-11-15 to the question whether DR-0029 lands as
     drafted; and the documentation registry, which refuses a decision record whose code span may
     be a command invocation (`docs_decision_execution_content`, `inline_invocation`).
   - **Considered:** revising the sentences that later decisions of the same day touch, such as
     the subject set of the candidate's condition; and narrowing the registry's rule so that the
     approved bytes pass.
   - **Chosen because:** the approval covers one text, and a later decision is a draft or a
     successor record that names this one, as the record itself requires. The approved draft named
     the hook installation command twice in a code span, in its sentence on the move of
     reclamation. No other decision record holds such a span, so the record follows the rule, and
     the sentence now names the command in words. Its meaning is unchanged and no other byte
     differs. The hosted run of the proposal ref found the refusal; the release lane's local check
     did not run the registry and now does.
   - **Applies to:** `docs/decisions/dr-0029-release-candidate-gate-successor.md`.
2. **The decisions README is the one pointer.**
   - **Rests on:** the README's rule that it is the only navigation among decision records, and
     the terminal plan's measured size of 500 nonblank lines against its bound of 500.
   - **Considered:** naming DR-0029 in the plan's release candidate paragraph, as the Change that
     added DR-0026 did for that record. It adds one line to a document at its bound.
   - **Chosen because:** what the paragraph says of DR-0026 still stands, and the README's entry
     names the succession, as it does for DR-0021 and DR-0027, which edited neither the records
     they narrow nor a plan.
   - **Applies to:** `docs/decisions/README.md`, and the plan's paragraph until the plan is
     divided.

## Risks / Trade-offs

- A reader who enters through the plan reaches DR-0026 and its withdrawn date first. The README's
  entry for DR-0029 says what it succeeds.
- The record is numbered 0029 while 0028 is not in the tree. That number is held for the test
  budget step, and no check requires consecutive numbers.
