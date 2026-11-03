# Design

## Context

See [proposal.md](proposal.md). A release run is a dispatch from `main` that names a signed tag and
its commit; `release-platforms` qualifies the release wheel on five legs and `release-publish`
writes the platform archives, the wheels, `ethos-<version>.mise.toml` with each platform's URL and
checksum, and `SHA256SUMS`, attests the archives and wheels and creates the GitHub prerelease. The
package acceptance already owns a fixture adopter with ephemeral signing keys, runtime activation
through the installed console, host-store pinning checks and a retained-state upgrade with its
rollback and reactivation (`prove_retained_upgrade`).

## Goals / Non-Goals

**Goals:**

- Each published prerelease passes the declared journey on macOS and Linux from its release assets,
  with evidence a reviewer can read.
- An already published prerelease can be qualified without publishing again.

**Non-Goals:**

- Windows and GitLab journeys, which the beta criterion does not declare.
- Publishing journey receipts as release assets; the release is created before the journey runs.
- Changing what the release run builds or publishes.

## Decisions

- **The journey installs what adopters install.** It downloads the release's Mise declaration,
  `SHA256SUMS` and its platform's archive, checks the archive against both, verifies its build
  attestation with `gh attestation verify`, and then lets Mise install the declared URL with
  `mise lock` and `mise install --locked`. Mise checks the downloaded bytes against the same
  checksum, so the installed archive is the attested one.
- **The previous release comes from the changelog.** It is the version whose entry follows the
  prerelease's, a reviewed and offline fact; its archive is checked against its own `SHA256SUMS`.
  Releases before `v0.2.0-alpha.29` carry no attestation, so only the subject's is required.
- **Fresh stores separate the cold install from the upgrade.** The cold install, hook binding,
  host-store pinning, full proof and status run in one fixture adopter on an empty host store; the
  upgrade from the previous release, its rollback and reactivation run through
  `prove_retained_upgrade` in a retained fixture adopter on a second empty store.
- **The full proof is the fixture's own floor.** The fixture adopter declares a signed two-gate
  registry, signature trust and patch validity, as its full proof set, and the journey runs
  `prove --full --execute` and `status` with the published console.
- **Uninstall keeps the pinned runtime.** After `mise uninstall`, the console is gone and the
  fixture adopter's status still answers from its pinned host-store runtime.
- **The journey code comes from the dispatching ref.** The job checks out the commit it runs on,
  not the tag, so a later accepted `main` can qualify an earlier prerelease, and a proposal can
  dispatch the journey alone while it is developed.
- **Mise installation has one owner.** `tools/ci/delivery/mise_tool.py` installs a declared tool in
  an isolated Mise home, offline for a local archive and online for a published URL; the
  distribution acceptance keeps its archive declaration and calls it.

## Risks / Trade-offs

- [The journey depends on GitHub's release downloads and runners] → It runs after publication, so
  a failure leaves the prerelease published and reports the failed step; a dispatch reruns it.
- [Each leg downloads two releases] → About 150 MB per archive; the legs run in parallel.
- [A journey failure after publication] → The release run reports it, and the prerelease is not
  promoted to beta until a journey passes.
