## Context

ETHOS already states that assistant files, MCP resources, host metadata, and
repo-local skills are projections over repository truth. The current
implementation does not enforce that distinction deeply enough: a
provider-visible `SKILL.md` can be a thin placeholder, while
`.agents/skills/activation.toml` acts as the only machine-readable playbook
record.

The V2 design keeps repository truth in source, tests, schemas, current docs,
promoted OpenSpec records, claims, evidence, and command JSON. It upgrades
skills from presence-only routing hints to quality-checked, digest-bound
workflow packages whose activation semantics are governed by ETHOS contracts.

## Goals / Non-Goals

**Goals:**

- Define a provider-neutral skill activation IR under `ethos-contracts`.
- Keep official skill packages real: loadable `SKILL.md` workflows with
  frontmatter, trigger boundaries, steps, evidence, and trust-boundary
  guidance.
- Keep `activation.toml` as ETHOS activation registry input, not provider skill
  metadata.
- Add strict validation so product proof fails closed while external adopter
  migration evidence remains modeled as historical replay fixtures.
- Add package manifests and capability classification for skill packages,
  scripts, MCP surfaces, and host projections.
- Make reports and proof distinguish skill presence from skill quality.

**Non-Goals:**

- Do not make skills, package manifests, MCP descriptors, or host metadata
  repository truth.
- Do not require reference adopter or other existing adopters to migrate to V2 before ETHOS
  can ship the product-root V2 gate.
- Do not introduce shell-script execution or arbitrary MCP mutation capability.
- Do not archive CL-002 or CL-003 until implementation evidence and claims are
  written after verification.

## Decisions

### Skill Contract IR belongs in ethos-contracts

The provider-neutral model belongs in `ethos-contracts`, not in
`ethos-assistants`. `ethos-assistants` reads registry inputs, validates skill
packages, emits projections, and routes tasks. It does not own the semantic
contract.

### Historical inputs normalize into a V2 IR

ETHOS v1 and reference-adopter-style `activation.toml` records remain readable as
historical replay fixtures. alternate activation style `skill_activation_contracts.toml`
is supported as a fixture input. Importers preserve fixture fields and add V2
enrichment rather than breaking existing shadow parity.

### Strict mode fails closed

`v2-strict` rejects placeholder skills, missing package manifests, missing path
coverage, stale commands, stale package digests, and missing proof obligations.
Historical replay fixtures keep adopter records readable without adding a
current product mode.

### Skill packages are authority-thin but package-real

`.agents/skills/<id>/SKILL.md` is still a projection over repository truth, but
it must be a real official-quality workflow package. Package manifests bind the
workflow files, required sections, capabilities, and digest state. A package
may expose commands or MCP surfaces only through declared capability classes.

### Projection drift is observable

Projection reports include package, registry, generator, and input digests.
Generator or digest drift makes projections stale. Host metadata can support
display and tool affordances, but it cannot introduce authority, gates, or
lifecycle semantics.

## Risks / Trade-offs

- **Strict mode can break existing adopters** -> Keep external adopter
  migration evidence as historical replay fixtures until refreshed evidence
  exists.
- **Digest fields can destabilize parity output** -> Keep shadow semantic diff
  focused on route readiness and ignore additive digest enrichment.
- **Package manifests can become a second authority** -> Treat manifests as
  package inventory and capability declarations only; activation authority
  remains in the ETHOS skill contract registry.
- **Docs could overclaim before behavior lands** -> Update current docs only
  after tests and implementation establish the behavior, then write evidence
  and claims last.

## Migration Plan

1. Add OpenSpec artifacts and failing tests.
2. Add V2 IR and schema validation.
3. Normalize v1 and alternate mechanism corpus inputs into the IR.
4. Add strict playbook check and route mode.
5. Add skill package manifest validation and capability classification.
6. Add scaffold, projection drift, report, repository-audit, and proof integration.
7. Migrate the ETHOS product root skill package.
8. Preserve reference-adopter v1 parity, refresh evidence only after verification.
9. Write dated evidence and claims, then archive the OpenSpec change.
