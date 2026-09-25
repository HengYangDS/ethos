# Design

## Context

The Linux ARM64 supply image is pinned by digest in the CUE CI source and
checked GitLab projection. Its `/opt/ethos-supply/input.sha256` binds the Node
runtime declaration, Python and npm manifests, and both lockfiles. The accepted
checkout differs in four of those five files, so `bootstrap-python.sh` refuses
the old image before any quality job runs. See [the proposal](proposal.md) for
the delivery impact. GitHub's quality job separately failed two adopter tests:
`uv lock --offline` ran from a temporary repository while `UV_CACHE_DIR` was
relative to that repository, not the supplied checkout cache. The same
relative path reproduces the failure locally.

## Goals and Non-Goals

The goal is to restore an exact image-to-checkout input match and keep the
GitHub offline cache stable across child working directories. This Change does
not alter dependencies, disable the bootstrap assertion, change CI jobs, or
claim a versioned release.

## Decisions

### Build from the accepted GitHub object

Use the existing trusted `supply-image` workflow on `dev`, and verify the run's
source SHA, published GHCR tag, immutable digest, and embedded input manifest.
The image is a distribution artifact, not a local build result. Building it on
the maintainer host or changing `input.sha256` by hand would make the checkout
appear healthy without proving the supply chain.

### Keep CUE as the Forge source

Update the one image declaration in `.config/ci/pipeline.cue`, render the
GitLab YAML through the existing CUE compiler, and update the GitLab emulator's
checked image coordinate in `.config/checks/ci/templates.toml`. The latter is
an execution selector whose equality with the hosted image is tested, not a
second release authority. Do not edit generated job logic or the GitHub
workflow by hand to work around a stale digest.

### Bind cache supply at each provider's execution root

Keep the shared CUE environment contract typed, but remove its relative cache
defaults. GitHub explicitly binds UV and CI-tool caches to
`${{ github.workspace }}`; GitLab retains its existing absolute image paths.
Every subprocess then sees the same supplied cache even after changing its
working directory. The generated GitHub workflow is checked against CUE, and
an architecture test rejects a relative cache regression. Changing the test
to download online would mask the failure rather than preserve offline proof.

### Publish per peer from fresh receipts

After local checks and exact-HEAD proof, use ETHOS publication receipts and
read back each remote ref and hosted run. A previously published peer does not
authorize another. The old GitLab CI failures remain historical facts; only a
new source commit and its own jobs can close this failure.

## Risks and Recovery

- **Trusted build fails:** inspect that run; leave the stale image pin and the
  fail-closed GitLab jobs in place until a valid image exists.
- **Digest or manifest differs:** reject the candidate image. Rebuild from a
  corrected accepted source rather than replacing the declared hash.
- **A peer changes during publication:** the receipt's exact compare-and-swap
  stops the effect. Reobserve and derive a new receipt; never force-push.
- **A selected peer publishes but another does not:** report the partial state
  and continue only with a fresh request for the remaining peer.
- **A cache path still moves:** the focused adopter quality test and hosted
  GitHub job must pass with the workspace-anchored cache before a CI claim.

## Delivery Order

Read back the trusted image, update and verify both checked projections, prove
the committed source, accept it locally, then publish and inspect each Forge.
Keep the Change active until source and hosted observations satisfy its tasks;
archive only through the official ETHOS/OpenSpec transition.
