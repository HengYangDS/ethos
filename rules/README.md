# Rules System

Rules are short executable guidance. They are neither a second architecture,
a task ledger, a plan store, nor an authority order. The semantic kernel and
carrier model are owned by the [Product Design Contract](../docs/governance/product-design-contract.md).

## Rule Record

Each durable rule states exactly:

| Field     | Requirement                                                                                                                           |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Authority | The owner whose duty the rule carries: a PDC section, an accepted requirement, or the narrow native carrier, command, schema or test. |
| Trigger   | The observable event that activates it.                                                                                               |
| Action    | The imperative action or prohibition.                                                                                                 |
| Evidence  | The command, artifact, or verifier that proves compliance.                                                                            |
| Stop      | The condition that blocks an effect, retirement, or closeout.                                                                         |

Delete or demote prose that cannot supply this record. Common semantic principles
apply to ETHOS and every governed repository. A rule may describe a profile-selected
carrier or native tool without making that implementation globally mandatory.
The repository supplies applicable native evidence, not a copied ETHOS toolchain.
Rules state duties; Skills route methods and cannot waive those duties.

## Entry Points

| Concern                          | Rule surface                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------------- |
| Agent behaviour                  | [Agent Rules](agents.md)                                                                      |
| Mutation and lanes               | [Mutation Rules](mutation.md), [Hook Rules](hooks.md)                                         |
| Module ownership                 | [Module Layout Rules](module-layout.md)                                                       |
| Evidence and attestations        | [Evidence Rules](evidence.md)                                                                 |
| Release and provider projections | [Release Rules](release.md)                                                                   |
| Declarative compilation          | [Declarative Lifecycle Rules](declarative-lifecycle.md)                                       |
| Optional skill adapters          | [Skill Rules](skills.md); [ETHOS source portfolio](../.agents/skills/README.md "source-only") |

## Placement

The Product Design Contract's carrier map
([Feedback Intent Preservation](../docs/governance/product-design-contract.md#feedback-intent-preservation))
and the [Docs Registry](../docs/governance/docs-registry.md#semantic-authority-and-carrier-boundaries)
owner table place each kind of meaning; rules carry only concise operational duties.

## Upstream Enforcement

Repeated late failures must move to the earliest enforceable boundary:

```text
observation → native declaration → schema/default → hook → gate → projection
```

A rule is incomplete when normal mutation can bypass it. Conversely, an
unproven policy sentence is not made “stronger” by duplicating it across a
rule, skill, document, template, and CI file. One owner is strengthened; the
other surfaces project or link to it.
