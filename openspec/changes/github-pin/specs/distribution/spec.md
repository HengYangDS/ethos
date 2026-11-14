## ADDED Requirements

### Requirement: A release installs through one exact GitHub pin

A published release SHALL install through one Mise entry, `"github:HengYangDS/ethos" = "<version>"`
under `[tools]`, with `locked_verify_provenance = true` under `[settings]` and no other option for
that tool. Each release SHALL have one class, `attested`, `attested-main` or `checksum`, naming what
its bytes are verified against. No installation claim SHALL exceed what its verifier checked, and a
lock's provenance field alone SHALL prove nothing.

#### Scenario: The pin locks and installs a release dispatched from main

- **WHEN** the journey locks the pin of an `attested-main` release for every platform the release
  published and installs its own platform, both with the CI's bound Mise
- **THEN** each lock entry SHALL name that release's own archive, the digest its `SHA256SUMS` lists
  and `github-attestations`
- **AND** the install SHALL hold the console in `bin/` and one runtime in `runtime/<16 hex>`

#### Scenario: A lock in an earlier format is relocked in place

- **WHEN** the pin is locked into an existing lock of format version 3
- **THEN** the lock SHALL keep its format version and record `github-attestations` for the pin

#### Scenario: A release's class follows its dispatch

- **WHEN** a release was dispatched from `main` and its attestation's source commit is the commit
  its signed tag names
- **THEN** its class SHALL be `attested-main`
- **AND** a release dispatched from its tag ref SHALL be `attested`
- **AND** a release without attestations, or whose attestation names another commit, SHALL be
  `checksum`

#### Scenario: Changed bytes are refused at install

- **WHEN** the bytes behind a locked entry of the pin do not match that entry's checksum
- **THEN** the locked install SHALL refuse them

#### Scenario: Another repository's attestation is refused

- **WHEN** a lock entry of the pin names bytes that only another repository attested
- **THEN** the locked install SHALL refuse them, or the lock SHALL record no `github-attestations`

#### Scenario: A refusal that does not hold keeps every claim at checksum

- **WHEN** either refusal does not hold under a Mise release
- **THEN** the journey SHALL fail and its receipt SHALL name that refusal
- **AND** no installation under that Mise release SHALL be described as more than checksum-verified

#### Scenario: A local archive installs in the same layout

- **WHEN** the local install smoke installs its own archive offline from a `file://` table
- **THEN** the install SHALL hold the console in `bin/` and one runtime in `runtime/<16 hex>`

## MODIFIED Requirements

### Requirement: A hosted journey qualifies each published prerelease

After a release run publishes a prerelease, a hosted journey SHALL install it through the exact
GitHub pin, with provenance verification, on macOS and Linux and pass, in fixture adopters on fresh
host stores, a cold install, host-store pinning, hook binding, a full proof and status, an upgrade
from each predecessor with its rollback, and uninstall. A dispatch SHALL run the journey alone for
an already published prerelease.

#### Scenario: A prerelease is published

- **WHEN** a release run publishes a prerelease
- **THEN** the journey runs on macOS and Linux against its published assets
- **AND** each leg's receipt names the result of every journey step.

#### Scenario: A published prerelease is qualified again

- **WHEN** a dispatch names an already published prerelease for the journey alone
- **THEN** only the journey runs, and the release is not published again.

#### Scenario: Each leg installs through the pin

- **WHEN** a leg installs the prerelease or one of its predecessors
- **THEN** it locks the exact GitHub pin of that release and installs its own platform from the lock
- **AND** its receipt names the Mise release, each release's class and each lock's format version.

### Requirement: The journey installs only verified release bytes

The journey SHALL check each archive it installs against its release's checksums and, by its
release's class, against its build attestation's signer workflow, source ref and source commit,
before installing it. Without named predecessors, the previous release SHALL be the first earlier
changelog entry whose release the forge published; the receipt SHALL name each entry it skipped.
Each leg SHALL upload its receipt and stage events whether it passes or fails.

#### Scenario: A published archive does not match its release

- **WHEN** a downloaded archive's digest differs from its release checksums, or the prerelease's
  archive fails attestation verification
- **THEN** the journey fails before it installs that archive
- **AND** the leg still uploads its receipt and stage events.

#### Scenario: An earlier version was tagged but never published

- **WHEN** the changelog entry after the prerelease names a version that has no published release
- **THEN** the journey upgrades from the next earlier version whose release exists
- **AND** its receipt names the skipped version.

#### Scenario: An attestation names another source

- **WHEN** an `attested-main` release's attestation names another signer workflow, a ref other than
  `main`, or a commit other than the one its tag names
- **THEN** the journey fails before it installs that release's archive.

#### Scenario: A checksum-class release is installed

- **WHEN** a predecessor's class is `checksum`
- **THEN** the journey checks its archive against its release's checksums only
- **AND** its receipt names that class.
