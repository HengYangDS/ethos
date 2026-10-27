---
subject: ethos:glossary
role: reference
state: active
relations:
  projects: ../governance/product-design-contract.md#semantic-kernel
---

# Glossary

Status: active projection.

Purpose: keep ETHOS terms discoverable for humans, agents, docs, and command
outputs.

Canonical owner: [Product Design Contract](../governance/product-design-contract.md#semantic-kernel).

See also: [Command Plane](command-plane.md), [Kernel Model](../concepts/kernel-model.md),
and [Docs Registry](../governance/docs-registry.md).

## Command Plane

The public `ethos ...` command vocabulary. Other tools may execute underneath
ETHOS, but they do not become public workflow roots.

## Isomorphic Governance

The ETHOS governance shape in which the same kernel governs the ETHOS product
repository and other governed repositories. Different profiles change admission,
checks, adapters, and proof depth through profiles and adapters; they do not
create separate ontology roles, command planes, or truth stores. This is not
product cloning. Each repository keeps its domain shape while ETHOS judges its
change through the shared evidence-bound transition loop.

## Authority

The inputs of product judgment: current user instruction, repository truth, the
exact official OpenSpec projection, fresh Facts, applicable policy, and valid
Attestations. No reader-facing summary overrides them.

## Commitment

A transient deterministic value compiled from one exact official OpenSpec
projection. It contains only `schema_version`, `id`, and `acceptance`.

## Facts

Fresh observations of the repository and its governed environment. They are
re-observed for compilation and are not a persistent semantic entity or truth
store.

## TransitionPlan

The deterministic, transient plan compiled from Commitment, current Facts,
policy, and applicable Attestations. It is executed or discarded, never
promoted into a persistent lifecycle owner.

## Attestation

The persistent semantic entity that records a content-addressed observation,
judgment, proof, effect, or external assurance with its verifier and validity
boundary.

## Subject

The governed object, such as a repository, path, package, domain, surface,
evidence set, or release target.

## Change

An official OpenSpec Change: the sole tracked carrier of intent, design, specs,
task progress, and archive in a mutation-capable repository. ETHOS compiles its
exact Git-tree projection into a transient Commitment; paths and Git coordinates
stay fresh Facts, and related Changes are query views, not stored relations.

## Evidence

Digest-bound material carried by an Attestation and bound to its verdict.

## Model Promotion

The named conflict adjudication owned by the
[Product Design Contract](../governance/product-design-contract.md#model-promotion).
It is an algorithm, not a persistent entity.

## Accepted Root

The coordination checkout that should remain clean in routine work.

## Work Lane

An isolated lane for tracked mutation.

## Lease

The expiring relationship between one Work Lane and one holder. Its complete
state is `lane_ref`, `holder_ref`, `generation`, and `expires_at`.

## Proposal Ref

A `proposal/*` ref that projects a trusted object for review; review needs no
completed proof, and the ref never becomes an authoring lane.

## Exact CAS

A compare-and-swap effect that rechecks fresh source and target ref facts before
mutation and verifies the observed result afterward.

## Candidate

The local integration branch used before accepted-root fast-forward.

## Projection

A repo-authored or host-local view that is not repository truth by itself.

## Required Gap

A missing, failed, or unverifiable required condition listed in `required_gaps`.
A result that carries one cannot pass, and only `pass` authorizes an effect.

## Continuation

The pure, non-persistent projection of a schema-version-`2` result: `await-user`
when `user_decision_required` is true, otherwise `blocked` for a non-passing
verdict, `continue` when a passing result names its one `next_action`, and `done`
when it names none. `done` ends that observation, not the repository, delivery, or
unrelated work. It is recomputed, never a second lifecycle state; the
[Product Design Contract](../governance/product-design-contract.md#openspec-acceptance-and-closeout)
owns it.
