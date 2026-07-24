---
subject: ethos:release-0-1-0a2-design
role: plan
state: planned
relations:
  canonical_for: governed 0.1.0a2 release closeout
---

# ETHOS 0.1.0a2 Release Design

## Context

The accepted repository is locally proven, the two configured Git remotes are
reachable, and the current package version remains `0.1.0a1` despite the
substantial changes accumulated under `Unreleased`. No local or remote release
tag exists. Reusing `0.1.0a1` for the current accepted tree would contradict
the dated changelog entry from 2026-06-30 and would make two materially
different trees share one version.

## Decision

Cut the next alpha release as Python version `0.1.0a2`, npm version
`0.1.0-alpha.2`, and signed Git tag `v0.1.0a2`.

Three approaches were considered:

1. Reuse `0.1.0a1`. Rejected because the changelog already binds that version
   to 2026-06-30 and current source has advanced materially.
2. Promote directly to stable `0.1.0`. Rejected because the repository still
   declares external package registries and several distribution adapters as
   deferred.
3. Increment the alpha serial to `0.1.0a2`. Selected because it preserves the
   current prerelease maturity while giving the current tree a unique version.

## Version And Changelog Contract

The release changes every active version carrier in one Work Lane:

- root and both Python package `pyproject.toml` files use `0.1.0a2`;
- `uv.lock` records the same version for all workspace packages;
- root and npm distribution manifests use `0.1.0-alpha.2`;
- `package-lock.json` records the same npm version;
- current-version assertions are updated while historical fixtures and the
  `0.1.0a1` changelog record remain unchanged;
- the existing `Unreleased` content becomes `0.1.0a2 - 2026-07-24`, followed
  by a new empty `Unreleased` section.

Version agreement is proven by the release-policy, npm, unit, architecture,
build, local-install, SBOM, and release-attestation gates.

## Publication Topology

Publication remains three separate transitions:

1. **Repository closeout:** prove the release commit, land it to
   `candidate/dev`, and close out accepted `dev` and release `main` at the exact
   same HEAD.
2. **Forge synchronization and observation:** perform non-force exact-ref
   pushes of `dev` and `main` to `origin` and `github`, then observe GitLab and
   GitHub pipelines independently until each required branch has a terminal
   result for the release HEAD.
3. **Release distribution:** create one SSH-signed annotated tag
   `v0.1.0a2`, push it without force to both remotes, and create prerelease
   entries on GitLab and GitHub containing the locally rebuilt Python and npm
   artifacts, checksums, SPDX-lite SBOM, and in-toto-shaped release
   attestation.

PyPI, TestPyPI, npm registry, Homebrew, Docker/OCI, GitHub Marketplace, and
GitLab Component publication remain outside this release because the canonical
product contract still marks them deferred. Forge release assets are the active
distribution surface for this closeout.

## Artifact And Evidence Flow

All release artifacts are rebuilt from the final accepted release HEAD in a
clean release Work Lane. The release bundle contains:

- two Python wheels and two source distributions;
- the npm launcher tarball;
- `SHA256SUMS` covering every distributed artifact;
- the ETHOS SPDX-lite SBOM envelope;
- the ETHOS in-toto-shaped release attestation;
- local release-policy, supply-chain, proof, remote, hosted-observation, tag,
  and forge-release evidence.

The post-publication evidence is stored in one immutable repo-family evidence
record. Generated files do not become repository truth merely because they
exist in `build/`; the record manifest and checksums bind the final evidence
set.

## Failure And Rollback Rules

- Any version-carrier mismatch blocks the release before land.
- Any proof, build, install, SBOM, attestation, or package failure blocks
  publication.
- Remote heads are re-read immediately before every push. Divergence blocks the
  push; no force option is permitted.
- A failed hosted pipeline is investigated and repaired through a new proven
  commit before tagging. A canceled or missing run does not count as success.
- The tag is created only after branch synchronization and required hosted
  observations succeed. A pushed signed tag is never moved.
- A partially created forge release is completed or explicitly recorded as
  partial; its tag and assets are not silently replaced.

## Acceptance

The release is complete only when the following facts are simultaneously
reproducible:

- `dev`, `main`, and `candidate/dev` equal the release HEAD locally;
- `origin/dev`, `origin/main`, `github/dev`, and `github/main` equal that HEAD;
- both forge pipelines report successful required jobs for the release HEAD;
- `v0.1.0a2` is an SSH-signed tag at that HEAD on both remotes;
- GitLab and GitHub prereleases exist for the tag and expose the same checksummed
  artifact set;
- the final repo-family record passes strict verification;
- the release Work Lane is clean, integrated, unoccupied, and retired through
  the owner-bound closeout path.

Valid-owner foreign Work Lanes remain protected throughout and are neither
mutated nor retired by this release.
