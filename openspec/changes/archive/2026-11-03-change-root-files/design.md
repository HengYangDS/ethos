# Design

## Context

See [proposal.md](proposal.md). When a Change is selected, current resolution
(`src/ethos/adapters/admission/current/resolution.py`) consumes `prospective_change_scope_report`.
It reports `openspec_change_path_mismatch:<selected>:<path>` for every path that starts with
`openspec/changes/<name>`, where `<name>` is neither `archive` nor the selected Change, unless the
path is preserved from a pending native merge.

## Goals / Non-Goals

**Goals:**

- A selected Change can write a file directly in `openspec/changes/`.
- A path inside another Change's directory stays refused.

**Non-Goals:**

- Choosing the Change for such a write: without a selection, several active Changes stay ambiguous.
- Relaxing patch admission, material scope or any other prewrite control.

## Decisions

- **A Change path has at least four segments.** `openspec/changes/<change>/<file>` is the shortest
  path inside a Change. The rule adopts the four-segment test that `artifact_path_change`,
  `preserved_incoming_change_paths`, archived-reference repair, the documentation registry and the
  OpenSpec audit already apply, so every rule that maps a path to a Change agrees.

## Risks / Trade-offs

- [A selected Change edits a shared guide] → The guide is an ordinary repository document. The
  selected Change's material scope, patch admission and review apply to it as to any document
  outside `openspec/changes/`.
