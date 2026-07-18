# Guard Publication-Topology Gap Collection

## Why

`release_policy_report` consumes `publication_topology` as an untrusted
read-model boundary. A malformed `required_gaps` value must not be iterated as
characters and promoted as invented release-policy failures.

## What Changes

- Treat only a list-valued `publication_topology.required_gaps` as release gaps.
- Preserve normal propagation for a declared list.
- Keep the change limited to the policy reducer and a focused regression.

## Capabilities

- `repository-governance`: subject=release-publication-gap-collection; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=quality; facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Changing GitLab/GitHub equality, remote configuration, publication execution,
  or release attestation policy.
