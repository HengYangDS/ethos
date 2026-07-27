---
subject: ethos:adopter-boundary-and-retirement
role: policy
state: canonical
relations:
  canonical_for: adopter migration, execution-substrate transition, and no-regression comparative proof
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
- bounded comparative-assurance proof Attestations; and
- effect and judgment Attestations for governed transitions.

The adopter owns domain truth:

- domain contracts and compatibility boundaries;
- repository-native tool configuration;
- canonical docs and decisions;
- durable evidence;
- repo-local skills and projections;
- domain-specific gates and accepted exceptions.

A profile changes required gates, proof depth, evidence classes, and adapter
bindings. It does not change ETHOS command semantics or kernel ontology.

Independent proof re-execution is one such adapter binding. It is default-off,
may be selected only for particular actions, and keeps provider identity, keys,
anchors, and receipt paths outside the adopter repository. A bounded
comparative-assurance proof Attestation must bind the target subject, verifier,
and evidence before it can support a governed transition.

## Comparative Assurance

A successor execution substrate may replace an incumbent only after it is proven
at least as strong for the adopter. This proof must use the same repository,
HEAD, changed paths, evidence inputs, structured comparative diff, and a clean
documentation-topology audit for the adopter target. The first transition gate is
the identity envelope: tracked evidence must bind target root, target HEAD,
product HEAD, compared command identities, changed paths, and evidence input
digests before semantic diff results can be used.

Allowed outcomes:

```text
successor == incumbent
successor stricter than incumbent
```

"Stricter" means the successor preserves every incumbent blocking
`required_gaps` item and may add additional blocking obligations. A missing
incumbent blocking gap is a comparative false negative even when the successor
records an advisory signal for the same condition.

Blocking outcomes:

```text
successor misses a required gap
successor accepts stale evidence
successor turns blocking into advisory
successor treats dry-run as live proof
successor loses domain gate planning obligations
successor permits removal while the common docs kernel is missing
```

## Exact Effects And Recovery

Switch, removal, and rollback are exact-HEAD/tree `effect` Attestations bound
to a reachable Git recovery anchor. Git revert alone is not sufficient recovery
evidence. Present configuration and Git state remain fresh `RepositoryFacts`;
comparison evidence remains a `proof` Attestation rather than a transition
state.

## Retirement Judgment

A retirement judgment must record:

- which capabilities transition;
- which surfaces remain adopter-owned;
- comparative evidence proving the successor is equivalent or stricter;
- profile validation evidence;
- domain false-negative evidence;
- exact-head/tree effects and their reachable Git recovery anchor;
- the deletion or retention scope; and
- what historical evidence remains derived.

Until that judgment is accepted, no effect is authorized. History supplies
context only and does not create a transition state machine.

Status: see front matter.

Purpose: define the no-regression lifecycle for moving adopter governance from
an incumbent execution substrate to a conforming replacement.

See also: [Repository Profile Contract](repository-profile-contract.md) and
[Config Boundary Model](config-boundary-model.md).
