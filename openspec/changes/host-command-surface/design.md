# Design

## Context

See [proposal.md](proposal.md). `src/ethos/surface/cli/application.py` registers each root from
`_COMMAND_MODULES`. The root help lists the six workflow commands, the MCP launcher, and the
semantically namespaced `attestation` and `host`. `lane` and `hook` are registered hidden.

## Goals / Non-Goals

Goals:

- Keep the surface test pinning the exact registered roots, now including `host`.

Non-goals:

- Any change to `ethos host run`, its visibility or its documentation.

## Decisions

- `host` stays visible. It is a semantic namespace that adopters' heavy commands must find, as
  `attestation` is. Hiding it would make the queue harder to join.
- The test, not the registry, names the expected set. A root added by accident still fails it.

## Risks / Trade-offs

- The root help grows by one line. The workflow commands stay the six that the specification
  names.
