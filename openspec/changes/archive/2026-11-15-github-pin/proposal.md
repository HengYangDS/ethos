# Proposal

## Why

A published ETHOS release installs through a table that each adopter copies: the release's
`ethos-<version>.mise.toml` declares an `http:` tool with one URL and one checksum per platform,
and nothing in that install checks who built the bytes. Every release run since 0.2.0-alpha.29
attests its archives, yet the hosted journey verifies the prerelease's archive only against the
repository, which any workflow and any ref of that repository satisfies, and it verifies no
predecessor at all. The product source holds no reader of a pin, of a lock entry or of what a
release's attestation must carry, so the Changes that select, write and move a pin have no owner
to call.

This Change is row C1 of the release-candidate order
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, Decision 2, Family 7); item 1 of that
design's Appendix C.2 is its done condition. The approved common-base design keeps the chain and
moves C1 ahead of `release-provenance`
(`openspec/changes/archive/2026-11-13-common-base-plan/design.md`, decision 4): the class of
releases that were dispatched from `main` closes by rule at the last such release, and C1 checks
each of them from the forge at its readiness. C1 is the first Change of the pin chain:
`pin-selection`, `adopt-pin` and `adopter-bump` call its module, and `release-identity` lands
beside it. It ships in 0.2.0-beta.11 under the release-candidate gate that DR-0026 records.

## What Changes

- A new product module, `ethos.repository.release.pin`, owns the pin: its key, its one-line and
  whole-file forms, readers of both declared forms and of lock entries in lock formats 3 and 4,
  each release's class and the attestation identity that a class requires. It holds pure functions
  over text and reads no file.
- The hosted journey verifies every archive by its release's class against the attestation's
  signer workflow, source ref and source commit, the commit that the release's signed tag names. A
  `checksum` release gets no attestation call. The check against the repository alone leaves.
- The journey installs the prerelease and each predecessor through the exact GitHub pin. Mise
  locks the pin, the journey admits each locked entry against the release's `SHA256SUMS` before
  any install, and the Linux x64 leg locks every published platform once, into a lock of format 3.
- Each leg rebinds the prerelease's own lock to other bytes twice, once to a changed checksum and
  once to an asset that only another public repository attested, and Mise must refuse both.
- The receipt also names the Mise release, each release's class, each lock's format and both
  refusals, and it keeps what a failed leg had established. A session option stops the journey
  once the classes are verified, which is how C1 checks the earlier releases from the forge.
- A local archive installs from a `file://` table that strips its top directory, so every
  installer holds the console in `bin/` and the runtime in `runtime/<16 hex>`.

Nothing changes what an adopter installs: the `http:` declaration is still published and checked,
and `http-retirement` removes it after the adopters' migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: ADDED requirement `A release installs through one exact GitHub pin`; MODIFIED
  requirements `A hosted journey qualifies each published prerelease` and
  `The journey installs only verified release bytes`.

## Impact

`src/ethos/repository/release/pin.py` and its unit test; the release journey, the Mise install
helper and the local distribution table under `tools/ci/delivery/`, the journey session in
`tools/ci/sessions.py`, the Mise platform name in `tools/ci/toolchain/native.py` and their unit
tests; `docs/governance/provenance-and-attestation.md`, `CHANGELOG.md` and
`openspec/specs/distribution/spec.md` through this Change's delta. Two shared carriers change by
one line each: `system/surfaces.toml` declares `GH_TOKEN` as a runtime input, since the install
helper now reads it, and `tests/fixtures/decision-density-baseline.json` moves one pin to the
function that now holds the pinned body, one point lower. `.config/ci/pipeline.cue` does not
change: the journey job already holds the token, the attestation permission and the tags.
