# Hook Rules

Purpose: place guards at the earliest useful failure point.

| Field | Rule |
| --- | --- |
| Authority | [Terminal Governance Product Design](../docs/architecture/terminal-governance-product-design.md), `ethos lane prewrite --json` |
| Trigger | Any host or tool supports a hook before context use, file write, shell execution, commit, push, or CI publish. |
| Action | Install the earliest hook that can block the invalid action. |
| Evidence | Hook report or equivalent command JSON shows target root, role, paths, and decision. |
| Stop | A normal write path can bypass `prewrite_guard` or context refresh. |

## Hook Layers

| Layer | Purpose |
| --- | --- |
| Context hook | Refresh repository truth when target root changes. |
| Pre-tool hook | Block unsafe `apply_patch`, IDE replace, shell write, MCP mutation, and generated tracked output. |
| Pre-run hook | Classify shell commands with tracked mutation potential. |
| Post-write hook | Fuse the session after unexpected paths or protected-root mutation. |
| Git hook | Commit-time fallback for deterministic local gates. |
| CI hook | Hosted integration, release, security, and supply-chain proof. |

Git hooks are fallback. The mandatory choke point for the accepted-root bypass
is the pre-tool hook.

## Context Binding

Pre-tool hooks must reject tracked writes when the tool call cannot prove:

| Field | Requirement |
| --- | --- |
| Target root | Absolute repository root for the intended mutation. |
| Editor root | Host/editor root when available, matching the target root when required. |
| Branch role | Current checkout role from `ethos status --json`. |
| Target paths | Repository-relative paths admitted by prewrite. |
| OpenSpec carrier | Required for non-trivial governance semantic changes. |

An implicit shell working directory, cached chat context, or IDE-selected root is
not sufficient proof. Wrong-root writes are a hook failure, not just an agent
mistake.

Pre-run hooks must reject `git stash` mutation commands because stash is a hidden
change carrier. `git stash list` and `git stash show` remain observation-only;
`push`, `save`, `apply`, `pop`, `drop`, `clear`, `store`, and implicit stash
creation are blocked with `git_stash_forbidden`.
