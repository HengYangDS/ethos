# Skill Rules

Purpose: define the canonical skill system and projection boundary.

| Field | Rule |
| --- | --- |
| Authority | [Skills](../.agents/skills/README.md), [Skill Activation](../.agents/skills/activation.toml), [Agent Projections](../docs/architecture/agent-projections.md) |
| Trigger | Creating, updating, routing, projecting, or invoking repo-local skills. |
| Action | Keep the canonical repo-local skill portfolio under `.agents/skills/` and treat host-native copies as projections. |
| Evidence | Activation entry, skill manifest, and post-check commands. |
| Stop | Skill duplicates docs, conflicts with rules, or creates host-specific truth. |

## Rules

- Add a skill only when repeated repository-specific procedure would otherwise
  be missed by a general agent.
- Keep each skill narrow and loadable. Put long explanation in docs or
  references, not in `SKILL.md`.
- `.agents/skills/activation.toml` is routing metadata, not authority over source,
  tests, docs, OpenSpec, or evidence.
- Every active subject-operation route has one owner. Retirement requires a
  reason, date, kill signal, and removal of any declared live carrier.
- Multi-skill activation is a compiled dependency closure. Declare only exact
  `requires` and `excludes` relations; permissive co-activation hints are not a
  lifecycle mechanism.
- Matched skill evaluations are evidence only; they never own tasks, progress,
  status, completion, or lifecycle.
- `.agents/skills`, `.claude/skills`, `.codex/skills`, IDE rules, and MCP
  prompt packs are projections unless the host owns an official native artifact.
- Generate OpenSpec Skills and supported slash commands only through the pinned
  official OpenSpec workflow, then characterize their version and use of
  official status/instructions. Do not copy or maintain local OpenSpec templates.
- Superpowers and other method packs are optional and never own repository
  tasks, plans, progress, or lifecycle state.
