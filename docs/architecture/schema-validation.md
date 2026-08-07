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
`base_commitment_digest`, and `commitment_binding`. The Lease state vocabulary
is exactly `valid`, `expired`, `unknown`, or `missing`; non-Work-Lane bindings use
`none`. This keeps invalid persisted state observable without converting it or
collapsing it to absence.

`ethos status --json` and `ethos lane status --json` validate the live
workspace-status payload before emitting it. The validation verdict is reported
as a `schema_validation` diagnostic that targets `data`; the `data` object stays
the raw workspace-status payload so existing consumers can continue to read
`data.role_policy`, `data.candidate`, `data.branch_bindings`, and
`data.closeout_support` directly.

Reference admission has no universal schema or coupling registry. Dependencies
are owned by package manifests, commands by the Cyclopts command tree, tools by
the tool and gate declarations, runtime inputs by the surface contract, and
forge coordinates by release and provider projection configuration. Prewrite
compiles that positive closure from the baseline tree and compares it with the
patch postimage; a patch cannot declare and consume a new reference in one step.

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
- `review-plan.schema.json` governs the exact-HEAD/tree/input-bound set of
  deterministic-first and judgment lenses compiled from current workload,
  intent, risk, capability, and path facts.
- `review-result.schema.json` governs one lens result and fixes
  `mints_authority = false`; review evidence can block or request a repair but
  cannot authorize an effect or become workflow state.

`system/review-lenses.toml` is the sole review-method declaration. Its ordered
dependency closure, token ceilings, blocking semantics, output schema,
freshness, and owner compile into the review plan embedded in `Facts` and thus
bound by the same `TransitionPlan` digest. Ambiguity or conflicting valid intent
requests human judgment; repairable findings remain agent work and are
recompiled after repair.

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
