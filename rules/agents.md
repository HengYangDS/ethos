# Agent Rules

Purpose: define how agents load repository truth and avoid stale context.

| Field | Rule |
| --- | --- |
| Authority | [AGENTS](../AGENTS.md), [Rules System](README.md), `ethos status --json` |
| Trigger | Starting work in this repository or crossing into this repository from another root. |
| Action | Load `AGENTS.md`, then `rules/README.md`, then the task-specific rule and skill surfaces. |
| Evidence | `ethos status --json` reports the target root and branch role. |
| Stop | Target path belongs to a different Git root whose `AGENTS.md` has not been loaded. |

## Rules

- Recompute repository root before acting on absolute paths.
- Do not reuse context from another repository after the target path changes.
- Treat host-local memory, IDE state, generated views, and chat output as
  context only.
- Use progressive disclosure: load the entrypoint, rule index, matching
  task-specific rules or skills, and direct references only. Do not bulk-load
  unrelated docs, archives, generated artifacts, or every skill unless the task
  is a broad audit.
- Before non-trivial governance design, rule, skill-system, hook, scaffold,
  release, evidence, or product-shape mutation, verify the dedicated OpenSpec
  change with `openspec status --change <change> --json`.
- Use repo-local skills from `skills/` when activation matches.
- Use official external skills as method packs; do not vendor their runtime
  instructions into repository truth.
