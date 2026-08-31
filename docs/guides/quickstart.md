---
subject: docs:guides
role: how-to
state: active
relations:
  canonical_for: first run
---

# Quickstart

Status: active.

Purpose: give a first-run path for inspecting a repository, binding an adopter,
planning proof, and reading the result without claiming a mutation.

See also: [Command Plane](../reference/command-plane.md) and
[Product Design Contract](../governance/product-design-contract.md).

## Product Repository

From the repository checkout:

```bash
uv run ethos status --json
uv run ethos plan --changed --json
uv run ethos prove --json
```

Read `required_gaps`, singular `next_action`, derived `continuation`,
`missing_facts_or_evidence`, and `user_decision_required` before changing
tracked files. The schema-version-`2` result preserves `state` and
`required_gaps`. A readiness result is not executed proof, landing,
publication, or remote push.

## Adopted Repository

Bind and inspect one external repository with the same command semantics:

```bash
uv run ethos adopt --root <repo> --json
uv run ethos status --root <repo> --json
uv run ethos prove --root <repo> --full --json
```

## Before a Tracked Write

Work only in an admitted Work Lane. Bind the exact checkout and target paths
immediately before editing:

```bash
uv run ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json
```

OpenSpec lifecycle operations remain official native-tool operations; use
`openspec validate --all --strict --json` when the change requires strict
workspace validation.
