---
subject: ethos:adoption-profiles
role: reference
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
docs/evidence/
claims/
.agents/skills/
```

The exact set is profile-driven and repository-owned. `.config/` remains the
execution/config layer; `.ethos/profile.toml` is only the ETHOS binding manifest.
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
