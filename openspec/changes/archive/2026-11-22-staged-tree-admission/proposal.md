# Proposal

## Why

The accepted requirement "Exact Index-target Prewrite Admission" says that the index-target
preview evaluates the prospective tree independently of working-file bytes, and that the commit
re-admits the actual staged content. Today both moments read the working files for OpenSpec. A
landing whose patch is whole is refused at the preview, and at the commit until the working files
hold the same content. A commit whose own content is whole is refused for a fault that sits in
the working files outside it. An adopter's landing lane is blocked on the first.

The owner moved this repair into 0.2.0-beta.12 on 2026-11-21.

## What Changes

- The OpenSpec scope of a staged admission is judged by its staged tree: the candidate tree at
  the index-target preview and the index tree at the commit. The tree's `openspec/` files and the
  carriers that a report needs are projected into a temporary directory, and the unchanged scope
  is evaluated there.
- The staged tree's answer stands when it passes, and the answer names that tree.
- A new obligation, `staged-openspec-tree`, enters as reporting. While it reports, a staged tree
  that does not pass, that cannot be observed, or whose evaluation fails leaves the verdict to the
  working files, as before this change, and its gaps are reported. No admission becomes stricter.
- The `pre-commit` hook prints one note for an admission that passes with reported gaps.

The preview without an index target, the worktree preview and a merge continuation are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The change moves the product toward the accepted requirement and changes no requirement
text, so `skip_specs: true` applies.

## Impact

Lane prewrite and the commit's staged admission; the OpenSpec projection; the paradigm's list of
reporting obligations; the hook's output.

Two refusals that the accepted requirement asks for are not delivered here: a staged tree that
cannot be observed, and a staged tree that fails beside whole working files. Both are reported. A
later release arms them by removing the obligation from the reporting list.

A commit passes while a fault sits in the working files outside it. Where the staged tree does
not pass, the admission evaluates twice.
