# Skill Portfolio Hardening

## Why

ETHOS skills were intentionally few, but the portfolio checks could still pass
when route surfaces overlapped, entrypoints became too broad, or package
boundaries drifted. In multi-agent development that leaves small routing signals
hidden until agents compete for the same semantic surface.

## What Changes

- Add strict skill markdown checks for trigger-focused descriptions and
  progressive-disclosure entrypoints.
- Add `portfolio_design` diagnostics to `ethos playbooks check` so path-glob,
  token, changed-scope, primary-subject, and package-size issues are visible.
- Narrow repository-governance routing so skill, quality, and lifecycle owners
  keep their own natural boundaries.
- Rebind skill package, registry, and projection-generator digests to the new
  repository truth.

## Non-goals

- No new top-level skill.
- No host-specific truth store.
- No provider-specific routing surface.


## Capabilities

- `ethos-assistants`: subject=skill-portfolio-hardening; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=skill; facet:surface=cli; facet:authority=source; facet:authority=test; facet:authority=evidence
- `ethos-contracts`: subject=skill-activation-ir; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema; facet:surface=skill; facet:authority=source; facet:authority=claim

## Out Of Scope

- Adding a new repo-local skill.
- Making host-native skill roots canonical.
- Replacing OpenSpec, evidence, claims, command JSON, or repository source with
  skill package metadata.
