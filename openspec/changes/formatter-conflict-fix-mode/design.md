# Design

## Context

See [proposal.md](proposal.md). `lane format` prepares the postimage of every selected file through
`prepare_source_format` before it branches on check or fix. A file whose shipped and local
configurations render different bytes raises `native_formatter_policy_conflict:<path>` there, and
`format_source` returns that refusal as a block.

## Goals / Non-Goals

**Goals:**

- The public fix journey refuses a conflicting increment before any write, and a test fails if a
  future change writes first.

**Non-Goals:**

- Compatible increments, the installed package and adopter migration, which the issue's original
  acceptance and the paradigm's own scenarios already cover.

## Decisions

- **Parametrize the two existing conflict tests by mode.** The check and the fix share the
  fixture, the expected gap and the byte assertions, so one test per increment covers both modes
  and no new fixture is added.
- **Assert the index too.** A fix that staged a postimage would leave the worktree bytes unchanged
  but change the index; comparing `git write-tree` before and after rules that out.

## Risks / Trade-offs

- [The fix cases pass because the fix is refused for another reason] → Each case asserts the
  `native_formatter_policy_conflict` gap, and the fix receives the current HEAD and authorization,
  so only the conflict can block it.
