# Proposal

## Why

`ethos lane format --check` and `--apply` refuse with `authored_text_path_invalid:<path>` when a
lane has deleted a tracked file without staging the deletion. Session 82cb0265 met it under
0.2.0-alpha.25 in filmkit, whose split replaced `tests/picture/picture.test.mjs`. A deletion is an
ordinary lane edit. `quality_source_files` (`src/ethos/adapters/gates/native/inputs.py:39-43`) lists
`git ls-files --cached --others --exclude-standard`, which keeps an indexed path after the worktree
deletes it, and `authored_text_gaps` then cannot read that path. Two consumers already work around
the listing: `native_repository_configuration` drops paths that do not exist (`inputs.py:216`), and
the content source's candidate members drop paths whose `lstat` fails
(`src/ethos/adapters/repo/content/source.py:34-45`).

The same session saw a focused proof of one gate refuse before execution with
`quality_obligation_unproven:<axis>` for the other axes of a multi-axis `code_correctness_map`. That
refusal is the quality floor: a focused selection that includes a code-correctness gate keeps every
mapped axis (`src/ethos/repository/policy/gates.py:187-208`). The refused plan's next action,
"repair the Commitment or repository facts" (`src/ethos/surface/cli/root/proof.py:355-365`), does
not name the full proof that selects every axis. A third refusal from the same session hides its
subject: `quality_behavior_javascript_native_test_scope_incomplete` names no file
(`src/ethos/repository/policy/quality_reports.py:503-519`), so the operator had to find that the
runner never entered `tests/picture/sample-film.mjs`, a shared helper without tests, before
declaring it `ethos-role=tooling` in `.gitattributes`.

## What Changes

- Candidate quality input is what the worktree holds: `quality_source_files` leaves out a tracked
  path that `git ls-files --deleted` reports, and `native_repository_configuration` drops its own
  filter.
- A focused proof refused only because unselected axes are unproven names
  `ethos prove --execute --json` as its next action.
- The JavaScript test-scope refusal names each selected test file that the runner never entered and
  each file it entered unselected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: candidate quality input omits a tracked file deleted in the worktree.
- `command-plane`: a focused proof that cannot meet the quality floor names the full proof.
- `quality`: the JavaScript test-scope refusal names the files that differ.

## Impact

`src/ethos/adapters/gates/native/inputs.py`, `src/ethos/surface/cli/root/proof.py`,
`src/ethos/repository/policy/quality_reports.py` and their tests; CHANGELOG `[Unreleased]`.
Adopters' `lane format` and every gate that reads candidate quality input stop refusing an unstaged
deletion. A proof of a committed head keeps its source-correspondence check
(`src/ethos/adapters/repo/gate_policy.py:422-440`), so it still refuses while a committed subject is
missing from the worktree.
