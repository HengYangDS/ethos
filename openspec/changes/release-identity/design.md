# Design

## Context

See the [proposal](proposal.md) and the [delta](specs/distribution/spec.md). "rc" is
`openspec/changes/archive/2026-11-07-rc-plan/design.md`.

- `AcceptedReleaseIdentity` holds a `BuildIdentity` (product and distribution version, source
  commit and tree) and `wheel_sha256`. Its Attestation, predicate `release:accepted-identity`,
  carries that projection as `payload.body.identity`. The reader already admits two forms, version
  1 (with `channel` and `acceptance_state`) and version 2, and re-issues the Attestation from the
  parsed identity to prove the record whole.
- The payload has three readers: release admission and runtime retirement, through
  `accepted_release_identities`, and the Attestation lifetime owner, which takes
  `identity.wheel_sha256` as the record's holder
  (`src/ethos/adapters/repo/attestation_lifetime.py`).
- `materialize_explicit_release` admits, stores, observes and attests one release wheel. It has no
  production caller; `release-acceptance` wires it behind `release accept`, which runs on the
  releasing host after the hosted journey (rc, Appendix C.2, item 4).
- The release assembler (`tools/ci/delivery/release_assets.py`) writes `SHA256SUMS` as
  `<digest>  <name>` lines, sorted by name, over the archives, the native wheels and each archive's
  two inventories, from the bytes it copied. The release run then attests the archives, wheels and
  inventories by pattern and creates the release; a failed step stops the job before the release
  exists.
- The hosted journey compares one archive with `SHA256SUMS` after publication
  (`release_journey_checksum_mismatch`). No product code reads the checksum file.

## Goals / Non-Goals

**Goals:**

- The accepted identity binds the version, the source tree, the checksum file's digest and every
  published wheel and archive by name and digest.
- Readers admit the earlier payload forms and the bound one, and an earlier payload yields the
  identity it recorded.
- `SHA256SUMS` is an attested subject of the release run, under the existing rule that a failed
  attestation stops the publication.
- A published file that disagrees with the checksum file refuses the acceptance with a gap that
  names it, before any effect.

**Non-Goals:**

- `release accept`, the publish refusal on `release_policy_report` and the global install; they
  are `release-acceptance`.
- Verifying the checksum file's attestation. The journey and the pin Changes own signer and source
  checks.
- Any change to the assembler, the journey or the `http:` declaration.
- Removing a reader, which is the contract step.
- Relaxing the wheel rule for a second host that accepts the same version.

## Decisions

1. **The bound form is version 3 of the same payload.** It keeps every version 2 field,
   `wheel_sha256` included, and adds `checksums_sha256` and `artifacts`, a mapping of file name to
   SHA-256. The lifetime owner and runtime retirement read `wheel_sha256` as before. Optional keys
   under version 2 were the alternative; a reader that predates this Change compares the whole
   payload and refuses either, so a distinct number costs nothing and says which form a record is.
2. **`artifacts` holds the wheels and archives of the checksum file.** They are the names ending
   in `.whl` or `.tar.gz`. The file's digest also covers the inventories it lists, but rc binds
   "every published wheel and archive". The accepted wheel is one of the published files, so its
   digest must be among them; otherwise the identity refuses with
   `accepted_release_artifacts_invalid`.
3. **One pure binding function in the admission owner.**
   `checksum_bound_release(release, checksums, published=)` takes the file's bytes and the digests
   that the caller observed, by name. It refuses a file that is not one ASCII `<digest>  <name>`
   line per name, compares each observed file with its line, and builds the bound identity through
   the constructor that the reader uses. It takes no path and reaches no forge, so the journey, a
   rehearsal and `release accept` can call it alike.
4. **The transition binds at admission.** With `checksums`, `materialize_explicit_release` binds
   before it reads the Attestation set, so a mismatch leaves the package store and the set
   untouched. The release already exists on the forge when a host accepts it; what the refusal
   precedes is the acceptance record, which is what public channels consume. The post-observation
   keeps covering the stored wheel, the transition's one effect, and the Attestation carries the
   admitted identity.
5. **Admission compares checksum files only when both identities carry one.** For one version,
   source and wheel, an identity without the binding and one with it agree, so a release accepted
   before the binding can be accepted again with it. Two bound identities with different file
   digests conflict as `accepted_version_artifact_conflict`. The wheel rule does not change.
6. **The Attestation names the checksum digest as evidence.** `sha256:<digest>` joins
   `evidence_refs`. `effect_digest` stays the wheel, which is what the transition stored.
7. **One more subject in the existing step.** `build/release/out/assets/SHA256SUMS`, the path the
   assembler writes, joins `subject-path`. The step keeps its place before release creation, so the
   existing rule covers it. The GitHub projection gains one line; the GitLab projection is
   unchanged.
8. **Not Breaking; the break belongs to the writer.** No recorded payload changes and nothing in
   this release writes version 3, so every consumer of the payload reads the bytes it read before.
   Once `release-acceptance` records a version 3 identity, an ETHOS older than this release refuses
   that Attestation set with `accepted_release_attestation_invalid`; the reader ships one release
   earlier for that reason. The contract step, which the common-base design places at the first
   0.3.0 build, removes the acceptance of a release without its checksum file (the transition's
   default) and the reader of the forms that carry no binding.

## Risks / Trade-offs

- No production path uses the binding in this release. Unit tests cover the binding, the readers
  and the transition; `release-acceptance` adds the first caller and its journey evidence.
- The attestation of `SHA256SUMS` is produced, not verified. No hosted run before the next release
  reaches the attestation step, and a failure there stops that release before it exists. The
  subject is the exact path the assembler writes; the first release run is read back (the workflow
  follow-up in the tasks), and verification by signer and source belongs to the pin Changes.
- An ETHOS older than this release refuses an Attestation set that holds a version 3 identity. The
  reader therefore ships first, and the writer follows one release later.
- A second host's acceptance of the same version still conflicts on the wheel. rc runs
  `release accept` once, on the releasing host; `release-acceptance` owns any change to that rule.
- The contract step meets the scenario that keeps earlier facts valid, "Runtime identity schema
  changes after a release". That Change must show that no retained Attestation carries an unbound
  form, or keep that reader and remove only the unbound writer.
- Three Changes of this batch edit `.config/ci/pipeline.cue`. This edit is one subject and one
  comment line inside the release step, and the lane regenerates the projections where it applies
  (task 4.1).
- A checksum line with a non-ASCII name, or with one space after the digest, is refused as
  malformed. The assembler writes ASCII names and two spaces; a release that used another form
  would need this reader changed first.
