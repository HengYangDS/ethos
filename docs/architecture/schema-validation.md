---
subject: ethos:schema-validation
role: explanation
state: canonical
relations:
  canonical_for: JSON protocol validation
---

# Schema Validation

Status: canonical.

Purpose: define the schema-governed JSON contracts that make ETHOS command output and kernel protocols automatable.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).

ETHOS command output and kernel protocols are JSON-first and schema-governed.

`ethos prove --gate schemas --json` validates tracked JSON Schemas with the
Draft 2020-12 validator. Command payloads use `system/schemas/kernel/result.schema.json`
as the stable envelope.

Workspace topology data is governed by
`system/schemas/kernel/workspace-status.schema.json`. The schema fixes the role
vocabulary, candidate fields, linked worktree entries, configured `role_policy`,
and role-policy `branch_bindings`. Release root and accepted root are separate
semantic roles. The role order is
release_root -> accepted_root -> candidate -> work_lane -> proposal_lane. Bindings
are ordered by that semantic order, then by branch name for additional bound
branches. Work Lane bindings include `lease_state`,
`base_commitment_digest`, and `contract_binding`. The Lease state vocabulary
is exactly `valid`, `expired`, `unknown`, or `missing`; non-Work-Lane bindings use
`none`. This keeps invalid persisted state observable without converting it or
collapsing it to absence.

`ethos status --json` and `ethos lane status --json` validate the live
workspace-status payload before emitting it. The validation verdict is reported
as a `schema_validation` diagnostic that targets `data`; the `data` object stays
the raw workspace-status payload so existing consumers can continue to read
`data.role_policy`, `data.candidate`, `data.branch_bindings`, and
`data.closeout_support` directly.

Coupling audit output is governed by
`system/schemas/kernel/coupling-audit.schema.json`. It exposes `binding_registry` as
the product classification vocabulary for hard bindings, mandatory
dependencies, native protocols, product-toolchain tools, adapters, historical evidence,
and fixtures. The branch role entry carries its configuration source, config
keys, default-policy state, semantic role order, and configured patterns. The
Work Lane lifecycle entry carries the standard ETHOS lifecycle commands and
the raw-worktree bypass state that is not admitted as standard ETHOS workflow.
Registry entries cannot carry host navigation, action, or label fields; those
are adapter projections, not coupling contract state.

Skills V2 adds three provider-neutral schemas:

- `skill-activation.schema.json` validates activation registry input such as
  subjects, path globs, operation metadata, lifecycle, package manifest paths,
  proof obligations, commands, and boundary fields.
- `skill-registry.schema.json` validates the normalized Skills V2 registry,
  including historical projection records and the stable registry digest.
- `skill-package-manifest.schema.json` validates package manifests for
  loadable `SKILL.md` packages, included files, digest algorithm, expected
  digest, required sections, quality flags, and capability classes.

`data.closeout_support` is part of the workspace-status schema. It exposes
whether the current checkout can be locally closed out to the configured
candidate branch, the target worktree path, the planned operation, the strict
Lease observation, its immutable base Commitment digest when valid or
expired, and the same required-gap vocabulary used by mutation admission.

Terminal semantic contracts are explicit:

- `commitment.schema.json` governs immutable intent, repository subject,
  material scope, invariants, acceptance, and authority references.
- `attestation.schema.json` governs one open-predicate statement with explicit
  evidence bindings; predicates carry meaning without a closed variant taxonomy.
- `facts.schema.json` governs freshly observed repository facts.
- `transition-plan.schema.json` governs deterministic transient transition plans.

Accepted OpenSpec capability identity and requirements live in each capability's
`spec.md`; schema validation does not maintain a parallel capability model.

`ethos prove --gate schemas --json` validates the schemas and sample contract
instances.

Schema validation is product governance. A command that returns JSON without a
tracked schema is not mature enough for automation.
`ethos prove --gate schemas --json` validates both schemas and representative
instances for docs registry, gate registry, workspace status, and Skills V2
contracts. Product-root runs also validate the live
`.agents/skills/activation.toml`, the normalized live skill registry, and every
live `.agents/skills/*/package.toml` against the Skills V2 schemas.
