# Tasks

## 1. Supply

- [x] 1.1 Pin Grype 0.121.1 for Linux and macOS and lock it. Done when `mise lock` records it for
      the four Linux and macOS platforms, and the locked install resolves `grype version` 0.121.1.
- [ ] 1.2 Bind a supply image built from the moved lock. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest.
- [ ] 1.3 Resolve Grype through the native supply. Done when tests show that the table-form
      declaration resolves its locked asset, that Windows on Arm is refused, and that Grype's
      version is read as JSON.

## 2. Scan

- [ ] 2.1 Add `tools/ci/release_binary_scan.py` and the `release_binary_scan` Nox session. Done
      when tests with fixture inventories and fake Grype output show five things:
  - a digest or subject mismatch refuses;
  - rows are keyed by archive, package, version and advisory;
  - npm rows count as audited only when the shipped lock matches;
  - a missing inventory reports its host as not scanned;
  - executables without packages are named.
- [ ] 2.2 Add the read-only `release-binary-scan` job after `release-publish`, with
      `continue-on-error`. Done when the GitHub projection is regenerated and conforms.
- [ ] 2.3 Accept inventory input on real archives. Done when, for the alpha.29 macOS, Linux and
      Windows x64 archives, the `sbom:` and `dir:` advisory pairs are equal under one Grype and
      one database, with run time and output size recorded.

## 3. Specification and notes

- [ ] 3.1 Add the `distribution` requirement. Done when strict validation and the cumulative
      archive simulation pass.
- [ ] 3.2 Name the change in the Unreleased notes. Done when the changelog validates.
