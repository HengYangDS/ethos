# Change Template

Create these files under `openspec/changes/<change-id>/`.

## proposal.md

```markdown
## Why

Explain the problem and why existing capabilities are insufficient.

## What Changes

- Describe the promoted repository surfaces that will change.
- Describe proof, rollback, and closeout expectations.

## Capabilities

- `ethos-repository`: subject=<stable-subject>; reuse=<reuse|extend|extract|new>; change=<add|modify|remove|rename|retire>; facet:lifecycle=<authoring|validation|runtime|archive|release>; facet:surface=<cli|docs|schema|openspec|evidence|skill|mcp|scaffold|ci|package>; facet:authority=<source|test|schema|docs|openspec|claim|evidence>

## Out Of Scope

- State what this change deliberately will not do.
```

## design.md

```markdown
## Context

Name the official OpenSpec boundary and the ETHOS repo-local product boundary.

## Design

Explain ownership, routing, proof, rollback, and promotion targets.

## Alternatives

Explain why reuse or extension is insufficient when creating or extracting a capability.

## Proof Strategy

Name static checks, executed proof, OpenSpec validation, and evidence locations.
```

## tasks.md

```markdown
## Tasks

- [ ] Update OpenSpec deltas.
- [ ] Update source/docs/schemas/tests.
- [ ] Bind claim and evidence.
- [ ] Run `ethos openspec --lifecycle --json`.
```
