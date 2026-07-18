## Context

`source-budget` is a whole-repository delta against a fixed baseline and named
deletion waves. It is valuable evidence for the global compression program, but
it does not establish whether a small current-contract behavior is correct.

## Goals / Non-Goals

**Goals:**

- Make the default promotion proof prove local correctness and governance.
- Preserve strict, separately actionable global source-budget visibility.
- Require source-budget in `--full` proof and global compression closeout.

**Non-Goals:**

- Do not hide, waive, reset, or relax source-budget policy.
- Do not claim a global compression closeout from a fine-grained Change.

## Decisions

1. Remove `source-budget` from `product_default`; retain it in `product_full`.
2. Move its scorecard projection from the hard local quality floor to a distinct
   non-blocking global-compression layer. This keeps the debt visible and
   actionable without making `report` or local land readiness stand in for the
   global program's closeout.
3. Keep the standalone command and exact report semantics unchanged.

## Risks / Trade-offs

- A small Change can reach local accepted closeout while global compression is
  still open. The separate scorecard layer and full proof prevent that state
  from being mistaken for program completion.
- A later global release/terminal closeout must run `ethos prove --full` and
  resolve the source-budget report before claiming compression completion.
