## Why

An adopter's public status reports PASS and offers landing while its own runtime
observation reports stale source. Runtime gaps currently reach the result only
through optional commit-policy enforcement, so omitting that unrelated policy
hides an independently required condition.

## What Changes

- Combine applicable runtime and commit-policy gaps independently in status.
- Select the existing exact runtime repair before a source transition, without
  reconstructing the repair command or changing mutation authorization.
- Preserve inspection of genuinely unadopted repositories and keep absent
  commit policy unconstrained.
- Verify missing, stale, current and unknown observations through the public
  reader, including adopted repositories with no commit-policy declaration.

## Capabilities

No new or modified specification requirement. This repairs the existing
`command-plane` requirement, "Hook runtime inspection exposes one exact repair
action", while preserving optional commit-policy semantics. The official
`skip_specs` marker declares that no specification delta is needed.

## Impact

The status aggregation owner, existing hook-binding public tests and canonical
terminal plan. No adopter files, dependency, runtime format or parallel carrier.

## Non-Goals

No policy requirement for generic adopters, automatic installation, changed
timeouts, capability downgrade, new lifecycle or broad runtime rewrite.
