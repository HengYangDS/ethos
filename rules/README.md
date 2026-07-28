# Rules System

Rules are short executable guidance. They are neither a second architecture,
a task ledger, a plan store, nor an authority order. The semantic kernel and
carrier model are owned by the [Product Design Contract](../docs/governance/product-design-contract.md).

## Rule Record

Each durable rule states exactly:

| Field | Requirement |
| --- | --- |
| Trigger | The observable event that activates it. |
| Owner | The narrow native carrier, command, schema, or test that owns its fact. |
| Required action | The imperative action or prohibition. |
| Evidence | The command, artifact, or verifier that proves compliance. |
| Stop | The condition that blocks an effect, retirement, or closeout. |

Delete or demote prose that cannot supply this record. A rule may describe a
profile-selected carrier but cannot make that carrier globally mandatory.

## Entry Points

| Concern | Rule surface |
| --- | --- |
| Agent behaviour | [Agent Rules](agents.md) |
| Mutation and lanes | [Mutation Rules](mutation.md), [Hook Rules](hooks.md) |
| Module ownership | [Module Layout Rules](module_layout.md) |
| Evidence and attestations | [Evidence Rules](evidence.md) |
| Release and provider projections | [Release Rules](release.md) |
| Declarative compilation | [Declarative Lifecycle Rules](declarative_lifecycle.md) |
| Optional skill adapters | [Skill Rules](skills.md) and [Skills](../.agents/skills/README.md) |

## Placement

- Semantic meaning and authority/currentness: canonical product contract.
- Machine-readable resolver and quality declarations: `system/`.
- Concise operational constraints: `rules/`.
- Active ETHOS self-profile delta: `openspec/`.
- Reusable agent procedures: `.agents/skills/`, as optional adapters.
- Native host/forge files: their host directories, as projections or narrow
  declarations.
- Immutable recovery and forensic bytes: repository-family records; their
  manifests prove package integrity, not current authority.

## Upstream Enforcement

Repeated late failures must move to the earliest enforceable boundary:

```text
observation → native declaration → schema/default → hook → gate → projection
```

A rule is incomplete when normal mutation can bypass it. Conversely, an
unproven policy sentence is not made “stronger” by duplicating it across a
rule, skill, document, template, and CI file. One owner is strengthened; the
other surfaces project or link to it.
