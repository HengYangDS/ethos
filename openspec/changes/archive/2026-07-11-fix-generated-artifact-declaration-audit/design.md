## Context

`generated_artifact_entrypoint_audit` currently builds `active_text` by stripping comments and blank lines, then applies denied-home token checks to every remaining line. That approximation works for shell and CI provider files but is unsound for structured manifests: a TOML value can describe cleanup, exclusion, or ignore policy without executing anything.

## Goals / Non-Goals

**Goals:**

- Audit executable task commands in `pyproject.toml` as producers.
- Ignore declaration-only path mentions, including cleanup and exclusion arrays.
- Preserve existing shell/CI producer checks and denied-home policy.

**Non-Goals:**

- Do not weaken path-topology checks for generated files that actually exist.
- Do not special-case alphasim paths or rewrite adopter manifests.
- Do not modify the concurrent runtime-topology Work Lane.

## Decisions

### Parse structured manifests before producer scanning

Use Python's TOML parser to extract command-bearing values from supported task tables instead of scanning the entire manifest text. Keep the existing line scanner for executable shell and CI files.

Alternative considered: extend `_is_cleanup_line` with more string heuristics. Rejected because ignore arrays and arbitrary declaration keys would keep producing false positives, and every new adopter syntax would require another textual exception.

### Retain a negative control for real task producers

Regression tests include both declaration-only mentions that must pass and a Pixi task command that writes to a denied home and must remain blocked.

## Risks / Trade-offs

- **Unsupported task-runner syntax is not scanned** → keep extraction explicit and extend it with tests when a supported repository introduces another command table.
- **Malformed TOML cannot be parsed** → fail conservatively by retaining the existing active-text fallback or reporting a parsing gap rather than silently approving executable content.
- **Concurrent lane overlaps the owner module** → stop before implementation until that lane is handed off, landed, or retired.
