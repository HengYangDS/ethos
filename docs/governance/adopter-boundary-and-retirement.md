---
subject: ethos:adopter-boundary-and-retirement
role: policy
state: canonical
relations:
  canonical_for: adopter migration, embedded implementation retirement, and no-regression shadow proof
---

# Adopter Boundary And Retirement

ETHOS is the product. Governed repositories are adopters. An adopter may be a
reference integration, dogfood repository, migration oracle, and rollback anchor
without becoming product ontology.

## Product And Adopter Ownership

ETHOS owns generic mechanisms:

- repository profile loading and validation;
- gate planning and evidence auditing;
- work-lane, proof, publication, and profile transition semantics;
- adapter command contracts;
- shadow comparison;
- retirement readiness checks.

The adopter owns domain truth:

- domain contracts and compatibility boundaries;
- repository-native tool configuration;
- current docs and decisions;
- durable evidence;
- repo-local skills and projections;
- domain-specific gates and accepted exceptions.

A profile changes required gates, proof depth, evidence classes, and adapter
bindings. It does not change ETHOS command semantics or kernel ontology.

## Migration Lifecycle

The safe lifecycle is:

```text
profile contract
-> dual-read compatibility
-> external shadow parity
-> reversible backend switch
-> embedded freeze
-> rollback window
-> retirement decision
-> embedded removal or historical archive
```

## External Greater Than Or Equal Embedded

An embedded implementation may be retired only after external ETHOS is proven
at least as strong for the adopter. This proof must be same repository, same
HEAD, same changed paths, same evidence inputs, structured shadow diff, and a
clean documentation-topology audit for the adopter target. The first retirement
gate is the shadow identity envelope: tracked evidence must bind target root,
target HEAD, product HEAD, compared command identities, changed paths, and
evidence input digests before semantic diff results can be used.

Allowed outcomes:

```text
external == embedded
external stricter than embedded
```

"Stricter" means the external product preserves every embedded blocking
`required_gaps` item and may add additional blocking obligations. A missing
embedded blocking gap is a shadow false negative even when external records an
advisory signal for the same condition.

Blocking outcomes:

```text
external misses a required gap
external accepts stale evidence
external turns blocking into advisory
external treats dry-run as live proof
external loses domain gate planning obligations
external permits embedded retirement while the common docs kernel is missing
```

## Rollback Window

A rollback window must include real use, not only dry runs:

- multiple proof and report runs;
- at least one Work Lane closeout;
- at least one domain gate planning path;
- at least one assistant or playbook route;
- one OpenSpec or Claim review path;
- one publish-readiness inspection.

Rollback must be configuration-based while the fallback exists. Git revert alone
is not sufficient rollback evidence. Once external ETHOS becomes the reversible
default, the adopter profile must expose a `[rollback_window]` table with a
tracked evidence manifest and completed minimum scenarios for proof/report, Work
Lane closeout, domain-gate planning, and assistant/playbook routing.

The evidence manifest is not a narrative placeholder. It must be tracked inside
the adopter repository, parse as TOML, bind the evidence to reachable adopter
and external-ETHOS heads, and include one entry per required scenario. Each
scenario entry records the scenario id, the evidence path, the command that
produced or checked the evidence, an evidence digest, and the same target and
product heads. Profile `completed_scenarios` are therefore admitted only when
the manifest independently proves the same scenarios.

## Retirement Decision

A retirement decision must record:

- which embedded capabilities migrated;
- which surfaces remain adopter-owned;
- shadow evidence proving external is equivalent or stricter;
- profile validation evidence;
- domain false-negative evidence;
- rollback-window evidence;
- which embedded packages, commands, and compatibility shims are deleted,
  frozen, or archived;
- what historical evidence remains.

Until that decision is accepted, the state is migration in progress, dual-run
phase, or external adoption preview. It is not embedded retirement.

Status: see front matter.

Purpose: define the no-regression lifecycle for moving adopter governance from
an embedded implementation to external ETHOS.

See also: [Repository Profile Contract](repository-profile-contract.md),
[Config Boundary Model](config-boundary-model.md), and
[Capability Parity Ledger](capability-parity-ledger.md).
