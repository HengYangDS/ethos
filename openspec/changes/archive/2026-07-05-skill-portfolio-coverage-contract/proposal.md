## Why

ETHOS already validates individual repo-local skill packages, activation routes,
and projection drift. The remaining weakness is portfolio-level shape: a registry
can contain valid skills while still missing the intended MECE owner set or
silently duplicating primary ownership. In multi-agent work this hides the small
signals that the portfolio is drifting into overlap or gaps.

## What Changes

- Add an activation-level portfolio coverage contract that declares required
  primary subjects and single-owner subjects.
- Make `ethos playbooks check --mode v2-strict --json` report deterministic
  required gaps when active primary skills fail that portfolio contract.
- Expose portfolio coverage results in the playbooks check payload and docs.

## Capabilities

- `ethos-assistants`: subject=skill-portfolio-coverage; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=skill; facet:authority=source
- `ethos-contracts`: subject=skill-activation-ir; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema; facet:authority=source

## Out Of Scope

- Adding new repo-local skills.
- Making host-native skill projections canonical.
- Turning skill activation metadata into product truth above source, tests,
  schemas, docs, OpenSpec, claims, evidence, or command JSON.
