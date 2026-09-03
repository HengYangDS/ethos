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

See also: [Documentation Root](../README.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).

ETHOS command output and kernel protocols are JSON-first and schema-governed.

`ethos prove --gate schemas --json` validates tracked JSON Schemas with the
Draft 2020-12 validator. Command payloads use `system/schemas/kernel/result.schema.json`
as the stable envelope.

Workspace topology data is governed by
`system/schemas/kernel/workspace-status.schema.json`. The schema fixes the role
vocabulary, candidate fields, linked worktree entries, configured `role_policy`,
and role-policy `branch_bindings`. Release root and accepted root are separate
semantic roles. The role order is
release_root -> accepted_root -> candidate -> work_lane. Governed `proposal/*` publication refs are not local role bindings. Bindings
are ordered by that semantic order, then by branch name for additional bound
branches. Work Lane bindings project the four-field Lease relation and a
`lease_state` of exactly `valid`, `expired`, `unknown`, or `missing`;
non-Work-Lane bindings use `none`. This keeps invalid persisted state observable
without mirroring Git or OpenSpec inside Lease state.

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
  including its current and retired projection records.
- `skill-package-manifest.schema.json` validates package manifests for
  loadable `SKILL.md` packages, included files, digest algorithm, expected
  digest, required sections, quality flags, and capability classes.

`data.closeout_support` is part of the workspace-status schema. It exposes
whether the current checkout can be locally closed out to the configured
candidate branch, the target worktree path, the planned operation, the strict
Lease observation, fresh Git coordinates, and the same required-gap vocabulary
used by mutation admission.

Terminal semantic contracts are explicit:

- `commitment.schema.json` governs the transient compiled
  `schema_version`/`id`/`acceptance` value.
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
