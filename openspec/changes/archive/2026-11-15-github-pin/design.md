# Design

## Context

See the [proposal](proposal.md). The hosted journey downloads a release's Mise declaration, its
`SHA256SUMS` and one archive, checks the archive's digest against both, and installs the declared
`http:` table through the shared Mise helper, which locks, installs with `--locked` and looks for
the console under the archive's own `ethos/bin`. Every proof's local install smoke installs a
`file://` table through the same helper and sets `bin_path` to reach that directory.

A release run is dispatched from `main` and names a signed tag, so its attestation carries the ref
`refs/heads/main` and the tag's commit, not the tag ref. One earlier release was attested from a
commit other than the one its tag names. DR-0018 judges a historical artifact by the attestation
made when it was produced, so each release keeps the identity of its own dispatch.

Mise's GitHub backend records `github-attestations` in a lock entry, and it has no option that
names a signer workflow or a source ref for a GitHub attestation: only `gh attestation verify`
checks those. Under Mise 2026.11.3 on one macOS host, an exact prerelease pin locks five platforms
without a prerelease setting, an asset pattern or a binary path, and the install strips the
archive's one top directory. Offline, the `http:` backend of Mise 2026.11.7 keeps the format of an
existing format-3 lock, reads the provenance setting from the project file and locks exactly the
platforms it is given. Whether a locked install checks the attestation again, and whether it
refuses foreign bytes, is not known.

## Goals / Non-Goals

Goals:

- One owner of the pin's form, of a lock entry's reading and of each release's class, which every
  layer and the Git hook path can import.
- A journey that installs as an adopter will, verifies each release by what its own dispatch
  attested, and fails when Mise accepts bytes that the lock does not bind.
- One installed layout for a pinned release and a local archive.

Non-Goals:

- Selecting a runtime from the pin, writing the pin at adoption and moving it at an upgrade: those
  are the three Changes that follow in the chain.
- Removing the `http:` declaration, its writer, the journey's check of it and the disk-image
  writer: `http-retirement` owns them, after the adopters' migration.
- A change to the release workflow: the tag-ref dispatch belongs to `release-provenance`, which
  also records where the class of releases dispatched from `main` ends.
- The Windows journey and a global install role.

## Decisions

1. **The pin module is pure and holds the distribution identity as a constant.** It uses the
   standard library and `packaging` only, reads no file and takes the platform from its caller. The
   key is the product's public repository, which is where every adopter installs ETHOS from
   whatever its own peers are, so it is not derived from a publication peer.
2. **A pin is one exact version.** `declared_pin` reads the string form and the table form of both
   keys. A version must be spelled as the version file spells a release, `X.Y.Z` or
   `X.Y.Z-<stage>.<N>`; a prefix, a range, `latest` or an unreadable configuration is
   `runtime_pin_invalid`, and a configuration that holds both keys is `runtime_pin_ambiguous`.
   Only the string form of the GitHub key is the bare form.
3. **Classes are data.** The module holds the first attested release, the releases whose
   attestation names another commit, and the last release dispatched from `main`, which stays
   unset while every attested release still is. `release_class` compares versions, so a release
   has one class however its version is spelled. `attestation_identity` gives the signer workflow,
   the source ref of the class and the tag's commit, and nothing for a `checksum` release.
4. **A lock is read, never trusted.** `lock_entry` and `lockfile_version` read lock formats 3 and 4
   alike and refuse unreadable text with `runtime_pin_lock_invalid`. The provenance field is what a
   lock records; a caller that needs evidence verifies the bytes.
5. **`gh` verifies signer and source, by class.** The journey resolves the tag's commit from the
   local signed tag and passes the three values of the class to `gh attestation verify` for the
   prerelease and for every predecessor. A `checksum` release needs neither a tag nor a call.
6. **Every install goes through the pin, and its lock is admitted first.** An attested release
   installs from the bare entry with the provenance setting; a `checksum` predecessor installs
   from the pin line alone, since nothing attests its bytes. Between `mise lock` and
   `mise install --locked` the journey requires, for each locked platform, the release's own
   archive name, the digest that `SHA256SUMS` lists and, outside the `checksum` class,
   `github-attestations`. The prerelease's lock starts from an existing lock of format 3 and must
   keep that format, and Mise must report the provenance setting as on. The Linux x64 leg locks
   every platform for which the release lists an archive; every other install locks its own.
7. **Two rebound locks must be refused.** Each is the prerelease's own lock with one platform
   entry changed, installed with `--locked` in a fresh scoped Mise home. The first changes one
   digit of the checksum. The second replaces the checksum, the URL and the API URL with those of
   an asset that another public repository attested, read from the product's own lock, and keeps
   the recorded provenance field. Observed on Mise 2026.11.8 in the hosted journey of 2026-11-15:
   Mise refuses that entry because its URL belongs to another release, before any attestation
   check, so the case proves that foreign bytes are refused and not which check refuses them. A
   lock with the release's own URL and another's attestation cannot be built. A case counts as
   refused when the install fails and leaves no installed tool. Both run directly after the
   prerelease's install, from the lock as Mise wrote it, so a refusal that does not hold fails the
   leg before its long steps.
8. **Only Mise's forge calls carry the job's token.** For a GitHub pin the lock and the install
   receive the job's `GH_TOKEN` as `GITHUB_TOKEN`, since anonymous forge calls are capped per
   address; the installed console and every other call do not. The surfaces registry declares
   the input, which the semantic closure requires of every environment value the tools read.
9. **The receipt is filled as the journey goes.** A failed leg keeps the Mise release, the
   classes, the locks and both refusal results it had established, which the refusal scenario
   needs. Every earlier field keeps its name and meaning. A journey that stops after the classes
   records the state `classes_verified`, never `passed`.
10. **One installed layout.** The local table sets `strip_components = 1` and no `bin_path`, the
    helper reads the tool's key from its declaration and the console from `bin/`, and the one
    runtime generation is read in one place. The archive's own layout does not change.
11. **The supply proof takes an installed tool.** A pinned install needs lock arguments, an
    existing lock and an admission step that a local archive does not, so the journey installs
    through the helper itself and the proof of the delivered supply is split from the local
    install. The local installer loses its declaration parameter, which has no caller left. The
    pinned complexity score follows the body to its new name and falls by one.

## Risks / Trade-offs

- What a locked install verifies is unproved, and only a hosted journey can prove it. If either
  refusal does not hold, this Change's done condition is unmet, every installation under that Mise
  release stays checksum-verified, and the release candidate's channel row follows.
- A locked install can also fail on a download or an API error. The receipt keeps Mise's message
  for each case, and the read-back accepts a case only when the message names its cause.
- The done condition binds the Mise release that CI's digest binds at readiness. Before
  2026.11.3 the bare form may select a wheel, so the supply move that raises that release lands
  first.
- Every predecessor is now verified by class. A release whose attestation does not bind fails the
  journey until the class data says `checksum`, so the forge check of the earlier releases runs
  before the first hosted journey, and a mismatch is a data change in this Change.
- The stripped layout changes the local install smoke of every proof, so it lands as its own
  commit and is proved there first. Until the journey's commit follows it, the journey still
  installs the published table, which Mise does not strip; no proof runs that path.
- The Linux x64 leg downloads every published archive at lock, about 2 GB more, within the
  ten-minute bound of one Mise call.
- The foreign asset is the first attested entry of the product's own lock for the leg's platform;
  a lock without one fails the leg.
- The journey module holds 482 of the 500 effective lines that one Python file may hold. The
  next Change that adds to it splits it first; the three functions of the pinned install are the
  natural part to move.
- A full journey on a developer host passes that host's `GH_TOKEN`, when one is exported, to
  Mise. The check of the classes alone runs no Mise call.
- The measured size is 105 product, 304 test and 197 tool line-equivalents against a planned 60, 80
  and 60. The plan priced the module's readers and the journey's lock admission, rebound locks and
  receipt at well under half of what its own list of them needs.
- DR-0020 counted this Change's unified installation at about 440 product line-equivalents when
  it took the product budget step; the installation that landed measures 105.
