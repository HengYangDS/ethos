## Why

The accepted source passes locally but three hosted bootstrap fixture cases fail
when the CI operator supplies a signing trust anchor. The fixture inherits that
unrelated host input while substituting a Python executable that cannot execute
the trust-binding branch, so the result depends on the runner environment.

## What Changes

- Give disposable bootstrap fixtures an explicit environment containing only
  their declared inputs, instead of importing workstation and CI authority.
- Exercise absent and explicitly supplied trust anchors through the real
  bootstrap transport and existing trust-binding owner.
- Preserve the failed hosted artifact, reproduce the distinguishing environment
  case, and verify local and hosted source outcomes separately.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This repairs test isolation without changing product requirements.

## Impact

The existing release/bootstrap test owner and canonical terminal plan. No
production signing policy, credential store, runtime dependency, adopter source,
or independent workflow is changed. Embedded Node/npm freshness remains separate.
