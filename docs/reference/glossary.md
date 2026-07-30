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

The authority used for product decisions: user instruction, repository truth,
accepted decisions, authority order, and truth boundaries. North Star language
is derived from this source; it is not the source.

## Commitment

The persistent semantic entity that owns immutable intent, authority references,
subjects, scope, permissions, hypotheses, and dependencies. Its identity is
content-derived; it does not own workflow state, and changed intent creates a
new Commitment.

## Facts

Fresh observations of the repository and its governed environment. They are
re-observed for compilation and are not a persistent semantic entity or truth
store.

## TransitionPlan

The deterministic, transient plan compiled from a Commitment, current
Facts, and prior Attestations. It is executed or discarded, never
promoted into a persistent lifecycle owner.

## Attestation

The persistent semantic entity that records a content-addressed observation,
judgment, proof, effect, or external assurance with its verifier and validity
boundary.

## Subject

The governed object, such as a repository, path, package, domain, surface,
evidence set, or release target.

## Change

The governed movement from one repository state to another, such as plan to
prove, Work Lane to candidate, candidate to accepted root, or release readiness.

## Evidence

Digest-bound proof material that supports Attestation verdicts and lifecycle decisions.

## Model Promotion

The named conflict adjudication owned by the
[Product Design Contract](../governance/product-design-contract.md#model-promotion).
It is an algorithm, not a persistent entity.

## Accepted Root

The coordination checkout that should remain clean in routine work.

## Work Lane

An isolated lane for tracked mutation.

## Candidate

The local integration branch used before accepted-root fast-forward.

## Projection

A repo-authored or host-local view that is not repository truth by itself.

## Required Gap

A blocking missing condition that prevents promotion.

## Proof Lattice

The state model that separates planned readiness from executed diagnostics and
trust-bearing proven evidence.
