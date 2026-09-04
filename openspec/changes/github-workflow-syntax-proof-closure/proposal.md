## Why

The accepted GitHub Actions projection contains an expression context that is
invalid at job-level `env`, yet the exact-HEAD full proof passed because its
existing actionlint owner is not selected by the canonical proof graph. Hosted
GitHub CI therefore became the first observer of a deterministic repository
syntax defect introduced at the same accepted commit.

## What Changes

- Make canonical full proof execute the existing GitHub workflow syntax owner
  exactly once, so invalid expressions and contexts fail before publication.
- Keep the hosted workflow template and generated workflow on one legal,
  repository-owned Python supply coordinate under `build/runtime/**`.
- Add an architecture regression binding the gate declaration, existing owner
  script, full-proof selection, and generated workflow projection.
- Do not add a checker, wrapper, registry, state carrier, compatibility path, or
  hosted-success substitute.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: require canonical exact-HEAD full proof to execute the existing
  deterministic GitHub workflow syntax owner before a hosted provider can
  become the first observer of workflow invalidity.

## Impact

The quality specification, canonical gate graph, GitHub Actions template and
projection, and focused architecture contracts change. The existing actionlint
configuration and owner script remain the sole workflow-syntax implementation;
no dependency, public command, persistent state, or adopter carrier is added.
