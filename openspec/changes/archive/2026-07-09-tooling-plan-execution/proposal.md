# Tooling Plan Execution

## Problem

The tooling adoption roadmap identified provider observation, dependency hygiene,
prose spelling, JSON Schema hygiene, and adapter-boundary work as follow-up
execution. Leaving those mechanisms as roadmap-only would keep useful local
invalid-state checks outside the active ETHOS gate floor.

## Change

Activate the locally executable owner gates that now have all five owner surfaces:
`deptry` dependency hygiene, `codespell` prose spelling, JSON Schema metaschema
validation, and hosted provider observation envelopes. Keep vulnerability
scanners planned because the current `pip-audit` path does not consume `uv.lock`
directly, and OSV scanner activation still needs pinned tool supply.

## Capabilities

- `quality`: subject=tooling-execution-gates; reuse=extend; change=add; facet:lifecycle=quality; facet:surface=ci,script,config,test; facet:authority=source,test,system,evidence
- `proof-hosts`: subject=hosted-provider-observation; reuse=extend; change=add; facet:lifecycle=evidence; facet:surface=provider,ci,evidence; facet:authority=source,test,config
- `adapters`: subject=adapter-profile-boundaries; reuse=extend; change=modify; facet:lifecycle=adapter; facet:surface=docs,quality-profile; facet:authority=docs,system,test

## Out Of Scope

- No hosted GitHub or GitLab success claim.
- No remote publication claim.
- No active vulnerability scanner claim for `pip-audit`, OSV, image scanning, or
  external signing.
- No promotion of Nox, Pixi, Pants, task ledgers, MCP, or agent method packs into
  ETHOS core ontology.
