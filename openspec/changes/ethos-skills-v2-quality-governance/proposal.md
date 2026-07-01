## Why

ETHOS currently treats repo-local skills as thin playbook projections, so
`ethos playbooks check` can pass when the only tracked skill is a placeholder
with no path coverage, no proof obligations, and no official-quality
`SKILL.md` workflow. This leaves CL-002 and CL-003 visible but unimplemented:
skills may fail provider expectations, and `activation.toml` can be confused
with provider-native skill metadata.

## What Changes

- Add a Skills V2 contract that separates ETHOS activation semantics from
  official skill packages.
- Normalize ETHOS v1, dmgr-style v1, and di-effect-style activation contracts
  into one provider-neutral skill activation IR.
- Add strict and legacy-compatible playbook validation modes.
- Require official-quality skill package manifests for loadable `.agents/skills`
  packages.
- Bind playbook reports, routing, projections, scaffold output, and proof gates
  to machine-readable skill quality and package-digest evidence.
- Preserve external adopter compatibility while making the ETHOS product root
  fail closed when skills are only presence-checked placeholders.

## Capabilities

### New Capabilities

- `skill-contracts`: Provider-neutral skill activation contracts, package
  manifests, capability classification, and digest binding.

### Modified Capabilities

- `ethos-assistants`: Replace thin playbook presence checks with Skills V2
  activation, package-quality, projection, and routing governance.
- `ethos-contracts`: Add provider-neutral schemas and IR for skill activation
  contracts and package manifests.
- `ethos-repository`: Surface Skills V2 gaps in scaffold, self-audit, proof,
  schema validation, and report scoring.
- `ethos-test`: Add conformance, migration replay, and parity fixtures for
  Skills V2 adoption.

## Impact

Affected areas include `ethos-assistants` playbook parsing and projection
checks, `ethos-contracts` schemas and IR, adopter scaffold generation,
repository self-audit and proof gates, shadow parity normalization, current
skill files, OpenSpec records, docs, evidence, and focused unit/architecture
tests.
