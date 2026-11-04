# Design

## Context

See [proposal.md](proposal.md) and the reviewed design in
`build/runtime/work/beta2/grype-design-draft.md`, including its reviews and the decisions of
2026-11-04 20:20 and 2026-11-05 01:05. Change `release-inventory`, which comes first in this
lane, publishes `ethos-<version>-<host>.syft.json` beside each runtime archive, with Go symbols,
covered by `SHA256SUMS` and the build provenance attestation.

## Goals / Non-Goals

Goals:

- Report the binary-level advisories of every published runtime archive, keyed so that two
  releases compare row by row, without downloading the archives again.
- Grype runs only in a read-only job, outside every landing and outside the job that holds
  release write permissions.

Non-goals:

- Blocking a release. Enforcement needs a binary subject in the dependency acceptance policy and
  an upstream-release lookup per bundled tool, which a later Change adds.

## Decisions

1. **Supply.**
   - Grype 0.121.1 is pinned with `os = ["linux", "macos"]`, so the lock holds only the hosts
     that scan.
   - The native supply learns `grype` and the table form of a declaration. A host outside the
     declared systems gets `native_tool_platform_unsupported:grype:<system>`, never a substitute.
   - The supply image is rebuilt and bound because `mise.lock` changes.
2. **Input.** The `release_binary_scan` session downloads `*.syft.json` and `SHA256SUMS` for the
   tag. Each inventory is refused unless:
   - its bytes equal its `SHA256SUMS` entry
     (`release_binary_scan_inventory_digest_mismatch:<host>`);
   - its source names the listed archive and digest
     (`release_binary_scan_inventory_subject_mismatch:<host>`).

   A listed archive without an inventory is `not_scanned`, never clean.

3. **Scanner.**
   - The native Grype runs `grype sbom:<inventory> -o json`, with its database in the CI tool
     cache.
   - The update check is off, and inherited `GRYPE_` and `SYFT_` variables are removed.
   - Grype's database validity check decides refreshes. No snapshot is pinned: the scan reports
     what is known now about what shipped, and the report records which database said so.
4. **Report.** `build/evidence/release-binary-scan/report.json` records:
   - the Grype version, and the database's build time, source URL and checksum, read from the
     URL's `checksum` parameter;
   - each host's archive and inventory digests, and its state;
   - one row per (archive, package, version, advisory), with type, severity, fix state and fixed
     versions;
   - for npm rows, `audited_by: "npm audit"` only when the shipped lock's SHA-256 in the
     inventory equals the scanned tag's `package-lock.json`, which the GitHub API returns, the
     lock that the release audit checked;
   - executables that Syft reports with no identified package, by archive and path.
5. **Placement.** The job `release-binary-scan` follows `release-publish`. It runs on
   `ubuntu-latest` with `contents: read` only and `continue-on-error: true`, and uploads its
   report. A `scan_tag` dispatch runs it alone, for an already published release, with the
   dispatching ref's code, as `journey_tag` runs the journey. Every other job skips that
   dispatch.

## Acceptance

For a Mach-O, an ELF and a PE archive of alpha.29, under one Grype version and one database, the
advisory pairs of `grype sbom:<syft json>` must equal those of `grype dir:<unpacked archive>`.
The run time and output size are recorded.

## Risks / Trade-offs

- The database download adds about a minute and a half to the release run, off the publication
  path.
- A new database entry can change a report between two runs of the same inventory. That is the
  scan's purpose, and the report records which database produced it.
