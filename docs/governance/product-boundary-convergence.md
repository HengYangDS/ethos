---
subject: ethos:product-boundary-convergence
role: policy
state: canonical
relations:
  canonical_for: reference-adopter migration and retirement safety
---

# Product Boundary Convergence

The ETHOS product repository is the product truth target.

A reference adopter is any governed repository selected through an adoption
profile as an integration fixture, migration oracle, or rollback anchor. The
identity and path of that adopter belong in profile and evidence records, not
in product semantics.

An embedded adopter-side governance implementation must not be deleted automatically. It may contain capability evidence that the product repository
has not fully absorbed.

## Lifecycle

The safe lifecycle is:

```text
Capability Parity Ledger
-> product migration
-> External Shadow Parity
-> reversible adopter backend switch
-> embedded freeze
-> Rollback Window
-> Retirement Decision
-> optional removal or archive
```

## Embedded Freeze

After the external product path becomes the default, the embedded implementation
enters frozen fallback / reference implementation status.

Frozen means:

- no new product features are added to the embedded implementation;
- the embedded implementation is not the default command backend;
- safety fixes, compatibility fixes, and parity fixes remain allowed;
- the embedded implementation can still support shadow diff, rollback, and
  historical mechanism comparison.

## Reversible Backend Switch

The adopter switch must be reversible. A representative control should preserve
both backends:

```text
ETHOS_BACKEND=external <adopter-runner> ethos status
ETHOS_BACKEND=embedded <adopter-runner> ethos status
```

The exact variable name may change, but the semantics must not: external and
embedded backends remain selectable through an explicit, low-risk mechanism
during the rollback window.

## External Shadow Parity

External Shadow Parity compares external ETHOS with the embedded reference-adopter
reference without changing the default backend.

Required comparisons include:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --json
ethos status --json
ethos assistants doctor --json
ethos playbooks route --changed --json
ethos --help
ethos land --json
ethos publish --json
```

The semantic diff must cover branch role, mutation allowance, changed-path
classification, required gates, required gaps, assistant boundary
classification, evidence freshness, land readiness, publish readiness, and
blocking versus advisory verdicts.

## Rollback Window

The rollback window must include representative real use:

- multiple proof and report runs;
- at least one real Work Lane closeout;
- at least one adopter-declared domain gate planning path;
- at least one assistant, playbook, or projection gate planning path.

## Retirement Decision

Only after the rollback window may a separate Retirement Decision decide whether
the embedded implementation is deleted, archived, or kept as a long-term frozen
fallback.

The executable pre-decision gate is:

```bash
ethos fleet retirement-readiness --target <repo> --json
```

This gate reads the adopter's `.ethos/profile.toml`, rejects product-core
adopter directories declared forbidden by that profile, checks tracked/live
shadow parity, requires `external>=embedded`, validates the profile-declared backend control manifest, requires the embedded backend to be frozen as
fallback/reference, runs the same generated artifact topology audit used by
product proof (`ethos prove --gate generated-artifacts --root <repo> --json`), and
verifies a generic `[rollback_window]` evidence manifest with completed
`proof_report`, `work_lane_closeout`, `domain_gate`, and `assistant_playbook`
scenarios before accepting a `retirement_ready` backend state. The manifest must
be adopter-repository local, Git-tracked, TOML-readable, bound to reachable
adopter and external-product heads, and backed by scenario entries carrying
evidence paths, commands, and digests. The final Retirement Decision remains a
separate governance act.

The decision must answer:

- what rollback path remains;
- what evidence proves external ETHOS can operate the reference adopter safely;
- which fixtures and tests migrate to `ethos-test`;
- whether an embedded snapshot is retained;
- which docs become historical material;
- which domain-specific mechanisms remain adopter-only.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
