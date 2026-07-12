---
subject: ethos:adoption-profiles
role: explanation
state: canonical
relations:
  canonical_for: repository adoption
---

# Adoption Profiles

Status: canonical.

Purpose: explain how ETHOS projects repository governance into adopters without copying adopter semantics into product core.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), [Glossary](../reference/glossary.md), [Repository Profile Contract](../governance/repository-profile-contract.md), and [Config Boundary Model](../governance/config-boundary-model.md).

`ethos adopt` projects ETHOS into another repository without copying adopter
semantics into ETHOS core.

The default adoption mode is strict: differing nonempty scaffold files stop the
apply before any write. This protects existing repositories from an accidental
governance replacement. An adopter that already owns its entrypoints,
documentation, OpenSpec workspace, or hosted-provider projection can request
an explicit non-destructive overlay:

```bash
ethos adopt --profile gitlab --overlay --dry-run --json
```

Overlay preserves those adopter-owned surfaces byte-for-byte and records their
paths and SHA-256 digests in the plan. It creates only missing ETHOS-owned
binding, local-state, skill, evidence, and generated-artifact surfaces; the
existing additive `.gitignore` merge remains the sole shared-file exception.
Differing `.ethos/**`, `.config/ethos/**`, ETHOS skill-package, and schema
placeholder files remain blocking conflicts even in overlay mode. Preservation
is a boundary record, not a claim that existing adopter semantics are valid or
that hosted CI has passed.

Supported profiles:

```bash
ethos adopt --profile generic --dry-run
ethos adopt --profile python --dry-run
ethos adopt --profile monorepo --dry-run
ethos adopt --profile github --dry-run
ethos adopt --profile gitlab --dry-run
```

Profiles create or validate a repository-level ETHOS binding entrypoint:

```text
.ethos/profile.toml
```

That profile references the adopter's existing governance and configuration
surfaces instead of replacing them. A typical adopted repository may expose:

```text
.config/
rules/
openspec/
docs/
evidence/
evidence/claims/
.agents/skills/
```

The exact set is profile-driven and repository-owned; adopters may map an existing `docs/evidence/` root through their profile, but ETHOS product truth uses `evidence/`. `.config/` remains the
execution/config layer; `.ethos/profile.toml` is only the ETHOS binding manifest.

Branch-role names are likewise adopter configuration, not product semantics.
An adopter whose lifecycle is not the default `work/* → candidate/dev → dev`
declares its existing names in `.ethos/workspace.toml`; for example:

```toml
[branch_roles]
release_branch = "master"
accepted_branch = "dev"
candidate_branch = "integration/dev"
work_branch_prefix = "task/"
submit_branch_prefix = "submit/"
```

The mapped candidate ref and worktree must exist before landing readiness can
be claimed. ETHOS does not invent a parallel branch train for an adopter.
ETHOS must not require `packages/`, `tools/`, `skills/`, `system/`, a monorepo
workspace, or any language-specific layout as the universal adopter shape.

GitHub and GitLab profiles may also generate hosted-CI projections and declare
those projections as provider surfaces. Hosted CI remains a projection over
repository-owned scripts and policies. The kernel remains profile-free;
repository-specific contracts stay in adopter profiles and adopter-owned docs,
rules, configuration, evidence, and skills.

Domain-specific gates are profile extensions. An adopter declares domain gate
mappings in its own profile, `ethos plan` selects those gates as repository
requirements, `ethos prove` records local evidence, and `ethos report` keeps
local readiness separate from hosted or domain-specific proof. ETHOS core does
not hardcode adopter domain names or treat generic command parity as domain
backend retirement readiness.

An adopted repository uses the same governed-repository command semantics as
the product repository, with profile-specific gates supplied by the adopter
profile and repository-native configuration.
Generated rules use `ethos report --json` for governance audit and
`ethos prove --json` for proof readiness. `ethos audit` remains the repository
governance depth command; adopter defaults do not create a separate command
plane.
