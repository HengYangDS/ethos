# Design

## Context

See [proposal.md](proposal.md). `quality_source_files` is the candidate inventory behind authored
formatting, prose, Markdown and configuration inputs (`authored_source_files`, `inputs.py:46-80`),
module layout (`src/ethos/adapters/gates/tool.py:545-553`) and the repository's native tool
configuration (`inputs.py:209-222`). Git's `--cached` listing reports the index, so a tracked file
the worktree deleted stays listed until the deletion is staged. `git ls-files --deleted` reports
exactly those paths: index entries whose worktree file is missing.

A focused proof resolves its gate policy with `selected_obligations` (`gates.py:343-346`). When one
selected gate verifies code, `_owner_projection` keeps every axis of the code correctness map
(`gates.py:187-208`), and `quality_verifier_gaps` refuses each axis whose mapped gate is not
selected (`src/ethos/repository/policy/quality/obligations.py:107-125`). The gaps refuse the plan,
whose next action is the generic "repair the Commitment or repository facts" (`proof.py:355-365`).

The Node probe compares the test files it selected with the files that the native runner's event
stream enqueued, and refuses any difference as `javascript_native_test_scope_incomplete` without
naming a file (`quality_reports.py:503-519`). A selected `.mjs` under a test root that holds no
tests is never enqueued; `ethos-role=tooling` in `.gitattributes` declares such a helper
(`src/ethos/adapters/repo/gate_policy.py:269-310`).

## Goals / Non-Goals

**Goals:**

- No quality consumer refuses or reads a tracked file that the worktree deleted, and one owner
  decides it.
- A focused proof that cannot meet the quality floor names the proof that can.
- A refused JavaScript test scope names the files that make it differ.

**Non-Goals:**

- Narrowing the floor to the selected axes: a focused run that selects code keeps every axis, so it
  cannot attest part of code correctness.
- The committed head's source correspondence (`gate_policy.py:422-440`), which a proof of that head
  keeps.
- The content source's candidate members (`content/source.py:34-45`): they need each member's mode
  and size from `lstat`, whose failure also drops a path that disappears between listing and
  observation.

## Decisions

1. **Git decides deletion.** `quality_source_files` subtracts `git ls-files --deleted` over the same
   pathspec from the candidate listing, so Git's own index-against-worktree comparison decides it.
   An unstaged deletion and a staged one select the same inputs. Rejected: an `exists()` check in
   each consumer (today's duplication); staging the deletion for the lane (a mutation it did not ask
   for).
2. **Consumers use the inventory as it is.** `native_repository_configuration` drops its existence
   filter. Module layout keeps `is_file()`, which selects regular files, not present ones.
3. **The refusal names the full proof.** When gates were selected and every required gap is
   `quality_obligation_unproven:<axis>`, the next action is `ethos prove --execute --json`, the
   proof whose selection includes every mapped axis. Any other refused plan keeps "repair the
   Commitment or repository facts".
4. **The scope refusal names its files.** The gap becomes
   `javascript_native_test_scope_incomplete:<path>[,<path>...]`, the sorted repository-relative
   paths of selected files never enqueued and enqueued files not selected, as other gaps name their
   path (`authored_text_path_invalid:<path>`). Rejected: a next action naming `.gitattributes`,
   since a file without tests may instead be a test the runner failed to load.

## Risks / Trade-offs

- [One more Git call per inventory] → `ls-files --deleted` reads the same index without hashing file
  contents.
- [A consumer depended on seeing a deleted path] → The committed proof keeps its own check of the
  head's subjects; the existing native-configuration case covers the moved carrier.

## Migration Plan

Land and release with the next alpha. Rollback: revert the Change.

## Open Questions

None.
