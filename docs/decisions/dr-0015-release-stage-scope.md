---
subject: ethos:decision:release-stage-scope
role: decision
state: canonical
decision_id: DR-0015
decision_status: accepted
relations:
  current_owner: ../governance/release-governance.md
---

# DR-0015: Release Stages Follow a Declared Journey Scope

Status: canonical rationale. Release Governance owns current behavior.

Date: 2026-10-24.

Purpose: preserve why a prerelease advances by evidence on the journeys its target declares, and
why an adopter's own environment is not an ETHOS release precondition.

See also: [Release Governance](../governance/release-governance.md#prerelease-stages) and the
`installed-product` OpenSpec Change.

## Context

ETHOS published 0.2.0-alpha.5 to 0.2.0-alpha.7 on 2026-10-21 and 2026-10-22 without a written
meaning for its prerelease stages. Release Governance said that stable readiness follows supported
journeys, but no release target listed its journeys. Every open task therefore read as a release
precondition. On 2026-10-24, 61 of the 100 open tasks waited on an adopter, a hosted or release
environment, or a user decision, and one adopter's hosted jobs on an intranet GitLab had been
treated as a condition for a release candidate.

Each of those alphas also showed a blocking defect within hours of adopter use. The Windows leg of
the 0.2.0-alpha.6 release stopped before its archive, and the 0.2.0-alpha.7 installation kept
writable directories into which a gate's interpreter wrote bytecode, so three adopters could no
longer select it. A stage rule has to catch such defects before a promotion, not after it.

## Decision

A product-release target declares the journeys it supports. Alpha covers any accepted increment.
Beta needs hosted verification on every supported platform, the declared adopter journey from the
published artifacts on macOS and Linux, and no known defect that corrupts an installation, blocks a
landing or admits a wrong proof. A release candidate is a beta that adopters used for 72 hours
without a new blocking defect, after which only fixes land; stable follows 7 such days of the
release candidate.

A journey that the target does not declare, or whose environment is unavailable, is named in the
release entry as not qualified instead of blocking the release. An adopter's adoption of a release
is that adopter's acceptance, tracked where the adopter tracks its work.

For 0.2.0 the declared journeys run from installation through Mise from the GitHub release to
release on macOS arm64, Linux x64 and arm64, and Windows x64. GitLab-hosted CI, GitLab publication
and the Homebrew channel are not declared for 0.2.0.

## Alternatives Rejected

- **Promote by age or landing count:** rejected because readiness follows journeys; three alphas in
  two days each still carried a blocking defect.
- **Require every open task:** rejected because most open tasks wait on environments outside the
  release, so the target could never be reached by work in this repository.
- **Require each adopter's hosted environment:** rejected because it turns an unavailable
  environment, such as an intranet GitLab, into a product gate; each adopter qualifies its own
  environment.

## Consequences and Boundary

- Open tasks keep their done conditions; a journey outside the target is named as not qualified,
  which weakens no task and no gate.
- A tag stays immutable; a defect found after it ships in the next prerelease.
- This record adds no checker or registry. Release preparation applies the stage rule, and release
  admission keeps owning version, entry, tag and artifact identities.

## Evidence and Revisit

- [Release Governance](../governance/release-governance.md#prerelease-stages) states the current
  stage rule and the declared 0.2.0 journeys.
- The 0.2.0-alpha.6 release run 39685244088 published no Windows archive; tasks 3.2.1 to 3.2.3 of
  `installed-product` sealed pinned installations and report payload damage after the
  0.2.0-alpha.7 bytecode incident.

Revisit when an undeclared journey's environment becomes available, such as GitLab-hosted CI, or
when a stage's observation period proves too short or too long for the defects adopters report.

The same day, [DR-0016](dr-0016-change-closure-scope.md) withdrew the tasks that waited on such
environments, or on in-repo work that 0.2.0 does not need, from their Changes; a task that stays in
a Change keeps its done condition.
