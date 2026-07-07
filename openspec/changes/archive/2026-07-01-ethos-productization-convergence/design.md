# Design: ETHOS Productization Convergence

## Authority and Kernel

The product model now starts with `Authority`. A North Star remains useful
as a reader-facing explanation, but it is derived from authority, user intent,
repository truth, accepted decisions, and proof. The lifecycle owner is
`Change`; `Claim` binds evidence to that lifecycle and is verifier-scoped.

The expanded terms `Contract`, `IR`, `Transition`, and `Inscription` remain
useful grammar inside `Commitment` and `Change`. They are not top-level owners.

## Command Surface

The product workflow is:

```text
status -> plan -> prove -> land -> publish
```

`report` is a read-only scorecard. Advanced commands stay reachable under the
same `ethos ...` root as maintainer/reference commands so operator escape
routes remain available without polluting the adopter first-hour path.

## Authority Graph

`docs/_meta/authority_graph.toml` is a typed read model. It records owner,
canonical target, derivation, supersession, evidence refs, and stable path, then
`ethos audit` reports drift gaps. The graph does not promote new truth by
truth; source, tests, schemas, docs, OpenSpec records, claims, and evidence do.

## Adoption Profiles

The supported profile names are `generic`, `python`, `monorepo`, `github`, and
`gitlab`. Dry-run output identifies read files, planned files, apply criteria,
and rollback.
