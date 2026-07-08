---
subject: ethos:glossary
role: reference
state: canonical
relations:
  canonical_for: shared terminology
---

# Glossary

Status: canonical.

Purpose: keep ETHOS terms discoverable for humans, agents, docs, and command
outputs.

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

## Subject

The governed object, such as a repository, path, package, domain, surface,
evidence set, or release target.

## Commitment

A rule or commitment that binds a subject. Contracts may come from schemas,
claims, OpenSpec families, release policy, quality policy, or adopter profiles.

## Change

The governed movement from one repository state to another, such as plan to
prove, Work Lane to candidate, candidate to accepted root, or release readiness.

## Evidence

Digest-bound proof material that supports claims and lifecycle decisions.

## Claim

A trust-bearing statement bound to evidence.

## Chronicle

The judged history index for decisions, evidence used, supersession, and current
state movement.

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
