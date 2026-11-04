# Design

## Context

See [proposal.md](proposal.md) and the reviewed design in
`build/runtime/work/beta2/grype-design-draft.md`, including its safety and leverage reviews and the
decision of 2026-11-04 20:20.

The hosted release run builds one runtime archive per host. It publishes them with `SHA256SUMS`
and a Mise declaration, then runs the adopter journey on macOS and Linux. Syft 1.56.0 is already
pinned through Mise. Grype 0.121.1 publishes builds for darwin amd64 and arm64, linux amd64 and
arm64, and windows amd64, but none for windows arm64.

## Goals / Non-Goals

Goals:

- Report the binary-level advisories of every published runtime archive, keyed so that two
  releases compare row by row.
- Keep the scan out of every landing and out of the job that holds release write permissions.

Non-goals:

- Blocking a release. Enforcement needs a binary subject in the dependency acceptance policy and
  an upstream-release lookup per bundled tool, which a later Change adds.
- Changing the release SBOM, which a separate Change brings to component level.

## Decisions

1. **Supply.** Pin Grype 0.121.1 in `.config/mise/config.toml` with `os = ["linux", "macos"]`, so
   the lock holds only the hosts that scan. The supply image is rebuilt and bound because
   `mise.lock` changes.
2. **Input.** The scan downloads the published archives, checks each against `SHA256SUMS`, and
   extracts it to a temporary directory. The pinned Syft catalogs it once (`syft scan dir:`),
   writing Syft JSON. The pinned Grype scans that file (`grype sbom:`). The catalog is the
   scanned inventory, so the published report and a later re-scan agree.
3. **Database.** Grype updates its database once per run, with its own validity check, and the
   report records the database's build time, URL and checksum. The application update check is
   off, and no ambient `GRYPE_` or `SYFT_` setting applies.
4. **Report.** `build/evidence/release-binary-scan/report.json` records:
   - one row per (archive, package, version, advisory), with severity and fix state;
   - npm rows marked as already audited;
   - binaries without package metadata listed by name;
   - a missing archive reported as not scanned, never as zero findings.

   The job uploads the report and the Syft JSON.

5. **Placement.** A job `release-binary-scan` follows `release-publish`, on `ubuntu-latest` with
   read permissions only and `continue-on-error: true`. It runs through one Nox session,
   `release_binary_scan`, as the journey does.

## Risks / Trade-offs

- The database download adds about a minute and a half to the release run, off the publication
  path.
- A new database entry can change a report between two runs of the same archive. That is the
  scan's purpose; the report records which database produced it.
