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

From the repository checkout, begin with the bounded reader:

```bash
uv run ethos status --json
```

Read `required_gaps`, singular `next_action`, derived `continuation`,
`missing_facts_or_evidence`, and `user_decision_required` before changing
tracked files. The schema-version-`2` result preserves `state` and
`required_gaps`. A readiness result is not executed proof, landing,
publication, or remote push. Follow only the selected boundary, not a fixed
status/plan/prove pipeline. When `continuation=done`, the requested observation
is complete; do not repeat it or create work merely to obtain another action.

## Adopted Repository

Preview binding of an unadopted repository; do not mutate it from this example:

```bash
uv run ethos adopt --root <repo> --json
```

The plan names the adopter profile and official OpenSpec config. Preserve the
existing repository layout and conflicting content; apply only the reviewed
plan, then observe status. Initial binding does not certify prior history or
prove scaffold, migration, uninstall, or crash recovery.

When current status selects verification, choose the required evidence depth:

```bash
uv run ethos prove --root <repo> --json
uv run ethos prove --root <repo> --execute --full --expect-head <exact-head> --json
```

These are alternative readiness and execution requests, not automatic steps.

## Before a Tracked Write

Work only in an admitted Work Lane. Bind the exact checkout and target paths
immediately before editing:

```bash
uv run ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json
```

OpenSpec lifecycle operations remain official native-tool operations; use
`openspec validate --all --strict --json` when the change requires strict
workspace validation.
