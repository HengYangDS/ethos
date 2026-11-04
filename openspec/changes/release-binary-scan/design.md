# Design

## Context

See [proposal.md](proposal.md) and the reviewed design in
`build/runtime/work/beta2/grype-design-draft.md`, including its reviews, the decision of
2026-11-04 20:20 and Revision 2 of 2026-11-05.

The hosted release run builds one runtime archive per host in its `release-platforms` legs. Those
legs have no write permission. `release-publish` assembles the qualified archives with
`release_assets.py`, attests them and creates the release. Syft 1.56.0 is already pinned through
Mise. Grype 0.121.1 publishes builds for darwin amd64 and arm64, linux amd64 and arm64, and windows
amd64, but none for windows arm64.

## Goals / Non-Goals

Goals:

- Each published runtime archive declares its components in an attested inventory, which is
  bound to the archive's digest.
- Each release reports the binary-level advisories of those inventories, keyed so that two
  releases compare row by row, without downloading the archives again.
- Syft runs only in jobs without write permission, and Grype runs only in the read-only scan job.

Non-goals:

- Blocking a release. Enforcement needs a binary subject in the dependency acceptance policy and
  an upstream-release lookup per bundled tool, which a later Change adds.
- The wheel SBOM of the `supply_chain` session, which stays as the landing's evidence.

## Decisions

1. **Supply.** Grype 0.121.1 is pinned in `.config/mise/config.toml` with
   `os = ["linux", "macos"]`, so the lock holds only the hosts that scan. The supply image is
   rebuilt and bound because `mise.lock` changes.
2. **Catalog at build.** After `install_smoke`, each leg runs the `runtime_inventory` session:
   - the source is `syft scan file:<archive>`, so Syft reads the archive's bytes and computes
     their SHA-256 itself;
   - `--source-name` gives the published file name, `ethos-<version>-<host>.tar.gz`;
   - `SYFT_GOLANG_CAPTURE_SYMBOLS=all` records the Go function symbols;
   - outputs are `runtime.spdx.json` and `runtime.syft.json` under
     `build/artifacts/release/inventory/`.

   The session refuses an inventory that does not name the archive's digest or that lists no
   component.

3. **Why two formats.** On the alpha.29 macOS archive, with one database:
   - Grype over the symbol-capturing Syft JSON reproduces exactly the 63 advisory pairs of a
     direct `grype dir:` scan of the unpacked runtime;
   - Grype over the SPDX reports 113.

   SPDX cannot carry symbols, so Grype cannot drop advisories whose vulnerable functions the
   binary does not link. Examples are Windows-only Go advisories in macOS binaries, and HTTP/2
   server advisories in tools that never serve.

   So the SPDX is the consumer-facing SBOM, and the Syft JSON is the scan input. The evidence is
   `build/runtime/work/grype/lane/acceptance/`.

4. **Admission at publication.** `release_assets.py` admits the two inventories of each job only
   when:
   - the SPDX `DESCRIBES` root has the published name and the archive's SHA-256 checksum;
   - the Syft JSON source has the same name and digest;
   - each lists at least one component.

   A one-package SBOM therefore fails as `release_assets_inventory_components_missing:<host>`.
   The assembler publishes them as `ethos-<version>-<host>.spdx.json` and `.syft.json`, adds both
   to `SHA256SUMS`, and keeps a per-host copy of the SPDX for its attestation.

5. **Attestation.**
   - One `actions/attest-sbom` step per release leg binds that host's SPDX to its archive. It is
     pinned to v4.1.0, `c604332985a26aa8cf1bdc465b92731239ec6b9e`, published 2026-03-18, and
     each step runs only when that host's SPDX exists.
   - The build provenance attestation adds both inventories to its subjects.
6. **Scan after publication.** The `release-binary-scan` job follows `release-publish`. It runs on
   `ubuntu-latest` with read permission only and `continue-on-error: true`, through the Nox
   session `release_binary_scan`.
   - It downloads `*.syft.json` and `SHA256SUMS`, checks each inventory's digest, and runs the
     pinned Grype on each.
   - Grype's database lives in the CI tool cache and updates with Grype's own validity check.
   - The application update checks are off, and no ambient `GRYPE_` or `SYFT_` setting applies.
7. **Report.** `build/evidence/release-binary-scan/report.json` records:
   - the Grype version, and the database's build time and source URL with its checksum;
   - each host's archive digest and inventory digest, with its state: `scanned`, or
     `not_scanned` with a reason;
   - one row per (archive, package, version, advisory), with severity, fix state and fixed
     versions;
   - npm rows marked as already audited;
   - executables that Syft reports with no identified package, by archive and path.

## Risks / Trade-offs

- Each release gains two inventories per archive, about 5 MB of SPDX and 7 MB of Syft JSON for a
  macOS archive. Each SPDX stays under attest-sbom's 16 MB limit.
- The database download adds about a minute and a half to the release run, off the publication
  path.
- A new database entry can change a report between two runs of the same inventory. That is the
  scan's purpose, and the report records which database produced it.
