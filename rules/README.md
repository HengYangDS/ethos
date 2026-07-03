# Rules System

Purpose: define the ETHOS rule kernel, authority order, entrypoints, and
mutation discipline for humans, agents, and tool hosts.

Rules are execution guidance over higher-authority facts. They are not a second
architecture store and must not restate long design material from `docs/`.

## Rule Kernel

Every durable rule must answer:

| Field | Requirement |
| --- | --- |
| Authority | Link to the code, test, doc, manifest, or command that owns the fact. |
| Trigger | State the event that activates the rule. |
| Action | State required behavior in imperative form. |
| Evidence | Name the command, file, or artifact proving compliance. |
| Stop | Name the condition that blocks mutation, validation, or closeout. |

Delete, demote, or move rules that cannot fill this record.

## Entry Points

| Audience | Entrypoint |
| --- | --- |
| Agents | [Agent Rules](agents.md) |
| Mutating tools | [Mutation Rules](mutation.md) and [Hook Rules](hooks.md) |
| Module layout, visibility, imports | [Module Layout Rules](module_layout.md) |
| Proof and claims | [Evidence Rules](evidence.md) |
| Release work | [Release Rules](release.md) |
| Skills | [Skill Rules](skills.md) and [Skills](../skills/README.md) |
| Hosts and tooling | [Agent Entry Points](../AGENTS.md) |

## Placement

- Put product architecture and terminal design in `docs/`.
- Put machine contracts and routing under `system/` when the terminal layout is
  implemented.
- Put concise operational rules in `rules/`.
- Put reusable agent procedures in `skills/`.
- Put host-specific projections in host-native directories only as generated or
  declared projections.
- Put OpenSpec change carriers under `openspec/`.
- Put proof under `evidence/` after the terminal evidence root exists.

## Failure Blocking Principle

Repeated late failures must move upstream:

```text
incident -> diagnosis -> rule -> hook -> scaffold/template -> schema/default
```

A rule is incomplete when the same violation can still bypass it through a
normal write path.
