# Design

## Context

See the [proposal](proposal.md). `_carriers` tells the product's own policy from a repository's
increment by path identity, and `paradigm_received_paths` already tolerates an increment it cannot
read; `format_ownership` does not, and the staged text check was its first caller under an
installed runtime.

## Goals / Non-Goals

Goals:

- Commits in the product's own repository pass `pre-commit` under an installed runtime.
- An adopter's byte-bound carriers stay excluded from the staged text check.

Non-Goals:

- Changing `_carriers` for the other commands that an installed runtime runs on the product's own
  repository, such as `lane format`; that follows as its own Change.
- Repairing the hook rollback, whose `ROLLBACK` runtime is no longer in the repository store, so
  `hook install --runtime` refuses it with `hook_runtime_manifest_invalid`.

## Decisions

1. `check_staged_text` computes the canonical-text paths with
   `canonical_text_paths(staged, canonical_resource(POLICY_PATH.as_posix()))` and skips the paths
   that `paradigm_received_paths(root, staged)` names.

## Risks / Trade-offs

- Under an installed runtime, a lane that edits the canonical-text rows of the policy is checked
  against the shipped rows until it lands; the source-format gate in the proof still judges the
  lane's own rows.
