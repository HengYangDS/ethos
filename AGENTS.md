# Agent Entry Points

This file is the neutral entrypoint for coding agents working in this
repository. It points agents to tracked repository truth without making any
vendor-specific assistant root canonical.

## Canonical Surfaces

- Project overview: [README](README.md)
- Contribution workflow: [CONTRIBUTING](CONTRIBUTING.md)
- Product design contract: [Product Design Contract](docs/governance/product-design-contract.md)
- Terminal target design:
  [Terminal Governance Product Design](docs/plans/terminal-governance-product-design.md)
- Rule system: [Rules System](rules/README.md)
- Agent rules: [Agent Rules](rules/agents.md)
- Module and semantic ownership rules: [Module Layout Rules](rules/module_layout.md)
- Mutation and Work Lane rules: [Mutation Rules](rules/mutation.md)
- Hook and guard rules: [Hook Rules](rules/hooks.md)
- Evidence rules: [Evidence Rules](rules/evidence.md)
- Release rules: [Release Rules](rules/release.md)
- Declarative lifecycle rules: [Declarative Lifecycle Rules](rules/declarative_lifecycle.md)
- Skill rules: [Skill Rules](rules/skills.md)
- Repo-local skills: [Skills](.agents/skills/README.md)
- Skill activation policy: [Skill Activation](.agents/skills/activation.toml)
- OpenSpec workspace: [OpenSpec](openspec/)
- Documentation index: [Documentation Index](docs/index.md)

## Authority Resolution

The current user instruction sets the objective and authorization boundary; it
does not turn an assertion, projection, or stale observation into repository
fact. Resolve every repository claim and effect contextually through
[`system/authority.toml`](system/authority.toml), using subject, predicate,
scope, plane, validity, and context.

Native carriers and fresh facts may be authoritative only for their declared
query. Projections, adapters, history, evidence, rules, skills, and host state
do not gain authority from a global rank. Unknown required facts, stale
bindings, ambiguity, contradictions, and unmodelled valid semantics block the
effect until the owning carrier is repaired or the model is promoted.

## Load Order

1. Read this file.
1. Read [Rules System](rules/README.md).
1. Read the rule file matching the task.
1. Use [Skill Activation](.agents/skills/activation.toml) to select candidate skills.
1. Run `ethos status --json` to read the checkout role, capability, gaps,
   visible Work Lanes, and unbound Work Lane refs.
1. Run `ethos plan --changed --json` before mutation planning.

## Agent First Glance

`ethos status --json` is the shared public reader for humans and agents. It
projects current repository state, actor capability, foreign Work Lanes,
unbound Work Lane refs, readiness gaps, and next commands; it does not mint
truth or authorize mutation.

For multi-agent concurrency, visible foreign Work Lanes and unbound Work Lane
refs are coordination signals by default. Visibility does not authorize write,
land, retire, or cleanup; those actions require owner handoff or maintainer
break-glass evidence.

Host-local memory, IDE state, generated views, and assistant outputs are context
only. They become repository truth only after promotion into tracked source,
docs, OpenSpec, or evidence.
