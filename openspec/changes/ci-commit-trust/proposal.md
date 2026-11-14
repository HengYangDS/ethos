# Proposal

## Why

The release-candidate gate's item R9 requires that no adopter builds ETHOS from source. One Python
service's CI still does, for one reason: CI commit trust has no released entry. Before
`ethos hook commit-range`, a CI job must bind the allowed-signers file that its operator supplies
to the checkout's `gpg.ssh.allowedSignersFile`, and only ETHOS's private
`tools/ci/toolchain/commit_trust.py` does that, so the service imports it from a source checkout.
The owner pre-approved that exception with this Change as its exit, and approved the
release-candidate scope on 2026-11-14 with this row in the first weekly batch (beta.11,
2026-11-21).

## What Changes

- A new operation of the `hook` group, `ethos hook bind-trust`, previews the binding of the one
  commit trust input that an operator supplies and performs it with `--apply`. Its inputs are
  `--anchor <path>` or the two existing environment variables; its refusals keep today's gap names.
- ETHOS's own GitHub and GitLab pipelines call the operation. The private module, its two helpers
  in `tools/ci/toolchain/environment.py` and their tests go; the product's test tree holds the
  cases.
- The command-plane reference describes the operation, and the Unreleased section of
  `CHANGELOG.md` gains an Added line.

Not breaking for adopters: the operation is new, and `ethos hook commit-range` is unchanged. A
caller that imports the private tools module from an ETHOS source checkout must call the operation
instead.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: ADDED requirement `CI commit trust has one released binding operation`.

## Impact

`src/ethos/application/hook/commit_trust.py`, `src/ethos/contracts/operations/hook.py`,
`src/ethos/application/catalog.py`, `tools/ci/toolchain/`, `.config/ci/pipeline.cue` with its two
projections, their tests, `docs/reference/command-plane.md`, `CHANGELOG.md` and
`openspec/specs/command-plane/spec.md` through this Change's delta.
