# Tasks

## 1. Supply

- [x] 1.1 Pin Grype 0.121.1 for Linux and macOS and lock it. Done when `mise lock` records it for
      the four Linux and macOS platforms, and the locked install resolves `grype version` 0.121.1.
- [x] 1.2 Bind a supply image built from the moved lock. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest. Run
      41884716472 built `ethos-ci-supply@sha256:2f71a037…` from `b44eab5a1`, and all five GitLab
      supply references select it.
- [x] 1.3 Resolve Grype through the native supply. Done when tests show that the table-form
      declaration resolves its locked asset, that Windows on Arm is refused, and that Grype's
      version is read as JSON. The 4 tests failed first and pass, and removing the system scope
      makes them fail. The supply architecture test reads the table form too.

## 2. Scan

- [x] 2.1 Add `tools/ci/release_binary_scan.py` and the `release_binary_scan` Nox session. Done
      when tests with fixture inventories and fake Grype output show five things:
  - a digest or subject mismatch refuses;
  - rows are keyed by archive, package, version and advisory;
  - npm rows count as audited only when the shipped lock matches;
  - a missing inventory reports its host as not scanned;
  - executables without packages are named.

  The 3 tests failed first and pass. Counting every npm row as audited, or dropping the
  database checksum, makes them fail. The report records the database's build time, source URL
  and checksum.

- [x] 2.2 Add the read-only `release-binary-scan` job after `release-publish`, with
      `continue-on-error`, and a `scan_tag` dispatch that runs it alone for a published release.
      Done when the GitHub projection is regenerated and conforms. It conforms, and the job test,
      which checks the dispatch input and that every regular job skips it, passes.
- [x] 2.3 Accept inventory input on real archives. Done when, for the alpha.29 macOS, Linux and
      Windows x64 archives, the `sbom:` and `dir:` advisory pairs are equal under one Grype and
      one database, with run time and output size recorded. Under Grype 0.121.1 and the database
      built 2026-11-04T06:20:59Z, the pairs are equal: 63 for macOS (Mach-O), 65 for Linux x64
      (ELF) and 130 for Windows x64 (PE). Cataloging takes 13, 19 and 11 seconds; the SPDX
      files are 5.2, 5.2 and 6.9 MB and the Syft JSON files 6.8, 7.0 and 7.3 MB, all under
      16 MB (`build/runtime/work/grype/lane/acceptance/formats.out`).

## 3. Specification and notes

- [x] 3.1 Add the `distribution` requirement. Done when strict validation and the cumulative
      archive simulation pass. Both pass, with all 12 specifications valid.
- [x] 3.2 Name the change in the Unreleased notes. Done when the changelog validates. The 139
      release tests pass.
