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

## Constitution

The repository operation charter: authority order, mutation boundary, public
command plane, truth/projection/context boundary, and release discipline.

## Contract

A rule or commitment that binds a subject. Contracts may come from schemas,
claims, OpenSpec families, release policy, quality policy, or adopter profiles.

## Evidence

Digest-bound proof material that supports claims and lifecycle decisions.

## Inscription

Tracked writes that change source, docs, config, schemas, evidence, projections,
or artifacts.

## Transition

The governed movement from one repository state to another, such as plan to
prove, Work Lane to candidate, candidate to accepted root, or release readiness.

## Accepted Root

The coordination checkout that should remain clean in routine work.

## Work Lane

An isolated lane for tracked mutation.

## Candidate

The local integration branch used before accepted-root fast-forward.

## Claim

A trust-bearing statement bound to evidence.

## Projection

A repo-authored or host-local view that is not repository truth by itself.

## Required Gap

A blocking missing condition that prevents promotion.

## Proof Lattice

The state model that separates planned readiness from executed diagnostics and
trust-bearing proven evidence.
