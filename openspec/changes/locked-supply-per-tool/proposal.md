# Proposal

## Why

`locked-supply-completeness` required every declared Mise tool to be installed before ETHOS returned
any locked tool or environment. Hosted CI installs some tools on first use, so the check refused
the CUE compiler of `ci-projection` on GitHub run `41815831007` and GitLab pipeline `14108`. The
reason was that Syft, scc, gitleaks and Vale were declared but not installed yet:
`mise_supply_incomplete:github:anchore/syft@1.56.0,...`. Local proofs passed because every tool was
installed on the host. The defect the check exists for is narrower: a resolution that returns
another tool's executable in a declared tool's place.

## What Changes

- `locked_tool` requires only the declared tool named after the requested executable to be
  installed, with the executable inside its install path.
- A locked environment refuses only a declared tool's own executable that resolves outside that
  tool, naming the tool as missing when it is not installed.
- A declared tool whose executable nothing resolves blocks nothing else, so supply can still be
  provisioned on first use.
- When `mise env` warns about a missing locked tool, the refusal names that tool and the step
  that can help.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the locked-supply requirement binds each resolved executable to its declared tool
  instead of requiring the whole declared supply.

## Impact

`src/ethos/adapters/toolchain/mise.py`, the toolchain and adoption tests, the `quality`
specification and the `0.2.0-alpha.30` notes.
