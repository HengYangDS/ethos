---
subject: ethos:adapter-lifecycle
role: explanation
state: canonical
relations:
  canonical_for: adapter lifecycle
---

# Adapter Lifecycle

Adapters begin as experimental projections. They become active only after they
prove stable input, output, failure, fallback, and retirement behavior.

Lifecycle:

```text
candidate -> experimental -> active -> deprecated -> retired
```

Retiring an adapter must not alter official OpenSpec intent, compiled
Commitment acceptance, Git facts, evidence, Attestations, or transition
semantics.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).

## Admission checklist

An adapter becomes active only when it has all owner surfaces:

1. a `system/tools.toml` entry that states profile, boundary, and gate;
2. an owner config under `.config/` or an adopter-owned native config;
3. a reusable `tools/ci/scripts/` or `ethos ...` execution surface;
4. CI/hook projection that invokes the owner surface without duplicating policy;
5. tests or proof that verify the boundary and forbidden assertions.

Environment runners such as Nox and Pixi, graph systems such as Pants, task
ledgers, MCP, and agent method packs remain adapter-only unless a future accepted
decision changes their binding class. Their output can route work or provide
observation evidence, but it cannot replace ETHOS proof, Attestations, OpenSpec
lifecycle checks, or Git-native Work Lane semantics.
