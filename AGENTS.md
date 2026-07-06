# Agent Entry Points

This file is the neutral entrypoint for coding agents working in this
repository. It points agents to tracked repository truth without making any
vendor-specific assistant root canonical.

## Canonical Surfaces

- Project overview: [README](README.md)
- Contribution workflow: [CONTRIBUTING](CONTRIBUTING.md)
- Product design contract: [Product Design Contract](docs/governance/product-design-contract.md)
- Terminal target design:
  [Terminal Governance Product Design](docs/architecture/terminal-governance-product-design.md)
- Rule system: [Rules System](rules/README.md)
- Agent rules: [Agent Rules](rules/agents.md)
- Mutation and Work Lane rules: [Mutation Rules](rules/mutation.md)
- Hook and guard rules: [Hook Rules](rules/hooks.md)
- Evidence rules: [Evidence Rules](rules/evidence.md)
- Release rules: [Release Rules](rules/release.md)
- Skill rules: [Skill Rules](rules/skills.md)
- Repo-local skills: [Skills](.agents/skills/README.md)
- Skill activation policy: [Skill Activation](.agents/skills/activation.toml)
- OpenSpec workspace: [OpenSpec](openspec/)
- Current docs index: [Documentation Index](docs/index.md)

## Authority Order

1. User instruction in the current session.
1. Repository source code, tests, schemas, and package metadata.
1. Machine contracts under `system/` when present.
1. Canonical docs under `docs/`.
1. OpenSpec records under `openspec/`.
1. Evidence under `evidence/` or current legacy evidence paths.
1. Rules and skills in this repository.
1. Host projections and generated assistant surfaces.

If these conflict, obey the higher authority and treat the lower surface as
stale until it is repaired.

## Load Order

1. Read this file.
1. Read [Rules System](rules/README.md).
1. Read the rule file matching the task.
1. Use [Skill Activation](.agents/skills/activation.toml) to select candidate skills.
1. Run `ethos orient --json` for first-glance role, capability, gaps, and visible
   Work Lanes.
1. Run `ethos status --json` before mutation planning.

## Agent First Glance

`ethos orient --json` is the shared reader view for humans and agents. It
projects current repository state, actor capability, foreign Work Lanes,
readiness gaps, and next commands from `status` and `report`; it does not mint
truth and does not authorize mutation.

For multi-agent concurrency, visible foreign Work Lanes are observe-only by
default. Do not write, land, or retire another lane unless the lane owner hands
it off or a maintainer records break-glass evidence.

Host-local memory, IDE state, generated views, and assistant outputs are context
only. They become repository truth only after promotion into tracked source,
docs, OpenSpec, or evidence.
