# Design

## Context

See the [proposal](proposal.md) and the [delta](specs/distribution/spec.md). "rc" is
`openspec/changes/archive/2026-11-07-rc-plan/design.md`; the first half is the archived Change
`2026-11-14-release-identity`.

- `release_policy_report` adds, to the role report that the repository audit already reads, the
  required release files, the version manifest, the exact `v*` tag policy, the host profile's
  surfaces, the attestation format and the publication topology's gaps. No command calls it.
- `observe_publication` (`src/ethos/application/publication/inspection.py`) already collects the
  audit's gaps, the topology's gaps and the proof admission for every target ref, and
  `blocked_publication_action` names the first report's next step.
- `materialize_explicit_release` admits a wheel against the accepted identities, stores it,
  observes the stored bytes and records one Attestation. The first half gave it the checksum file
  as an optional input. It has no production caller.
- The console re-executes every command but `hook install` into the runtime that the target
  repository's `CURRENT` selects (`run_console` in `src/ethos/application/console.py`).
  `selected_runtime_source` names the installed runtime that carries the running package, and
  nothing for a source checkout.
- rc installs the release as the releasing host's global `ethos` after the hosted journey, and has
  one release operation check its version and run the transition once (rc, Appendix C.2, item 4).

## Goals / Non-Goals

**Goals:**

- The product's release tag does not publish while its release policy holds a gap, and the result
  names the gap and a next step.
- One catalog operation accepts the release that the releasing host installed, with a typed next
  step, once.
- Every refusal precedes every effect and carries a registered repair.
- The release guide states the acceptance step and the undo.

**Non-Goals:**

- A release policy refusal for a governed repository. Its report-first form is the draft
  `release-ref-policy-report`.
- Installing the release. The host's one global owner installs it; ETHOS fetches nothing.
- Verifying the checksum file's attestation. The journey and the pin Changes own signer and source
  checks.
- The requirement `Release Policy` of the repository-governance specification, which names
  `ethos publish --json` and command owners that have retired. The readiness read does not call
  the report; that requirement keeps its own review.
- Removing the reader of an identity without the binding, which is the contract step.

## Decisions

1. **The operation is `release accept`, in a new hidden group `release`.**
   - **Rests on:** the catalog at the base, read from `COMMANDS` and `GROUPS`: 45 commands, 8
     groups and 107 operations. Three names hold the word: the command `attestation release` and
     the operations `land.release.preview` and `land.release.apply`; none holds "accept". The root
     help's test pins the shown groups as `attestation` and `host`
     (`tests/unit/cli/test_catalog_commands.py`).
   - **Considered:** a selector on `land`, whose request already has 16 fields and 8 operations,
     and whose module stands at 472 of 500 effective lines; a command under `attestation`, whose
     three commands act on any member of the set and know no release; a command under `hook`,
     which installs and guards a repository's runtime; and a shown group, which changes the root
     help that every agent reads for an operation that one host runs.
   - **Chosen because:** rc names the operation so and places its rehearsal reader in the same
     group later, so the name is the one a release Change will use. The cost is a second meaning
     of "release" beside `land --release`, which tags a head, and `attestation release`, which
     removes a member.
   - **Applies to:** the command path, its two operation IDs `release.accept.preview` and
     `release.accept.apply`, and the group's help. A hidden group still runs and still answers
     `ethos release --help --json`. The terminal surface test pins the registered roots and
     names `release` among them (`tests/unit/cli/test_terminal_command_surface.py`).
2. **The publish refusal holds for the product root only.**
   - **Rests on:** a measurement in a temporary root that declares `v*` tags and holds every
     required release file and no Python project. `release_role_policy_report` gives no gap
     there; `release_policy_report` gives `release_version_manifest_invalid`,
     `package_version_mismatch` and `attestation_formats_incomplete`. On the product tree the
     report gives none. DR-0029 states the law: no release adds a refusal to a tree that passed its
     predecessor unless an earlier release reported the rule.
   - **Considered:** refusing in every governed repository, as rc's sentence reads, which refuses
     the measured shape on its next release tag with gaps it cannot close without becoming a
     Python project; and reporting without refusing everywhere, which leaves the product's own tag
     unguarded.
   - **Chosen because:** the report states the product's conformance, and the product tree passes
     it today, so the refusal costs the product nothing and guards its next tag. The trade-off is
     that rc's sentence is met for one repository, and the others wait for the draft Change.
   - **Applies to:** a publication probe or apply whose target ref has the release tag role, in a
     root whose profile ID is the product's. Branches, transport tags, retirements of other roles
     and every other root read no product policy. Readiness without a target ref is not covered.
     The report reads the checkout, as the repository audit beside it does, so it states the
     tagged tree's policy only while the checkout's head is the tagged commit. A profile that
     cannot be read raises the profile's own gap and is never read as another repository.
3. **The gaps join the publication's own gaps, and the next step follows the topology's.**
   - **Rests on:** `observe_publication`, where each report's gaps close the local verdict, and
     `blocked_publication_action`, which names the first report that has a next step.
   - **Considered:** a separate verdict for the policy, which adds a second way to block; and
     placing the policy's step first, which hides the audit's exact repair for a gap both name.
   - **Chosen because:** one gap list and one ordered choice of step already exist. The audit and
     the topology name exact repairs for their own gaps, so they stay ahead; the policy's step is
     an instruction, since no single command repairs a version manifest or a host surface.
   - **Applies to:** `required_gaps`, `next_action` and `data.release_policy` of a publication
     with a target ref. The data prints the report because no other command prints it: a gap
     such as `package_version_mismatch` names no file, and its report does.
4. **The release to accept is the invoked installation.**
   - **Rests on:** `selected_runtime_source`, which answers for a running package inside an
     immutable runtime and never for a source checkout; `run_console`, which would otherwise
     replace the invoked installation with the repository's selection; and the release lead's
     reading of 2026-11-15,
     relayed and not run by this Change, that the wheel a published release lists for one platform
     has the file name of the wheel its installation holds.
   - **Considered:** a `--runtime <path>` option read under the repository's selection, which
     cannot show that the path is the host's global installation; and resolving `ethos` from the
     search path, which reads the environment for an identity.
   - **Chosen because:** rc's check is of the global `ethos`, and the operator reaches that
     installation by invoking it. The command therefore joins `hook install` as a command that
     runs in the invoking installation. Two costs: the operation knows the installation it runs
     in and cannot tell a global one from another install of the same release; and the SDK and
     MCP, which run inside the selected runtime, accept only when that runtime is the release.
   - **Applies to:** the console entry. The wheel is the one in the installation's package
     directory, admitted only when its digest is the manifest's.
5. **Absent, older and newer each refuse by name, against the version the accepted branch
   commits.**
   - **Rests on:** `committed_release_version`, the reader `land --release` uses for the same
     version; `is_release_build`; and the transition's own check of the wheel's build.
   - **Considered:** comparing with the newest tag, which a maintenance tag would mislead; and
     accepting any installed release that has a tag, which records an identity for a release the
     host is not releasing.
   - **Chosen because:** the releasing host accepts the release it just cut. A source checkout or
     a development build is `release_installation_absent`; another version is
     `release_installation_older:<version>` or `release_installation_newer:<version>`; a version
     without a tag is `release_tag_missing:v<version>`; and a wheel built from another commit than
     the tag names is the transition's `release_wheel_build_identity_stale`. The cost: once the
     accepted branch commits the next version, the previous release reads as older and is no
     longer accepted.
   - **Applies to:** the product root; any other root is `release_acceptance_product_only`. The
     expected build is the tagged commit and its tree, never the accepted head. The two
     versions are ordered as SemVer texts, the form of both carriers, so a committed version
     outside the wheel profile reads as older or newer and never as an unreadable one.
6. **The checksum file is required.**
   - **Rests on:** the first half's decision 8: the acceptance of a release without its checksum
     file is removed at the contract step.
   - **Considered:** an optional file, which gives the first production caller a path that writes
     the form the contract step removes.
   - **Chosen because:** rc gives the accepted identity every published byte, and the checksum
     file is how. An unreadable file is `release_acceptance_input_unreadable`.
   - **Applies to:** the request model, where the field has no default. The transition's own
     parameter stays optional for its tests of the earlier form.
7. **Admission is its own function, and a held identity writes nothing.**
   - **Rests on:** `record_attestation_once`, which returns the member the set holds, and
     `write_content_addressed`, which adopts an identical record again and restarts its retention
     floor.
   - **Considered:** calling the whole transition on every run, which touches the stored wheel
     each time; and a preview that repeats the admission's steps in the application module.
   - **Chosen because:** `admit_explicit_release` is the part of the transition before its first
     effect. It answers with the identity that stands: the candidate's when the set records
     nothing for the version, and the recorded one when the set holds it equal or different
     only in a checksum binding that one of the two lacks; and it says which. The preview and
     the second run call it alone, so they write nothing; the apply calls the transition, which
     reads the wheel once, admits the digest of those bytes and stores the same bytes. The
     transition attests the identity that admission named and refuses
     `identity_transition_attestation_mismatch` when the set returns another, so a record that
     another writer made in between is reported by the next run and never stands in for this
     one. Which record agrees with a candidate is one rule, `identities_agree`, that admission
     and the choice of the standing record both apply, so the choice does not rest on the
     check that ran before it. A refusal that carries no gap still blocks, named by its class.
   - **Applies to:** the states `ready`, `accepted` and `unchanged`. A passing preview's next step
     is the apply with the checksum file's absolute path; the other two are done. `unchanged`
     carries the recorded identity, so a checksum file presented after a record without the
     binding is checked against the wheel and not reported as bound. An operating system error
     of the apply, after its inputs were read, is `release_acceptance_store_unavailable` with
     the error's name, not an unreadable input.
8. **The module lives beside the land operations.**
   - **Rests on:** `CONTROL_PREFIXES`, which names `src/ethos/application/land/` and whose last
     widening needed the owner's acknowledgement; and the catalog's test that an entry of a group
     that writes lies under one of those prefixes.
   - **Considered:** a module directly under `application/`, which needs a new prefix; and the
     land operation module, which stands at 472 of 500 effective lines.
   - **Chosen because:** the acceptance closes the release that `land --release` opens, and a
     module of its own adds no line to a file near the bound.
   - **Applies to:** `src/ethos/application/land/release_acceptance.py`.
9. **Each new refusal carries its repair in the gap registry.**
   - **Rests on:** `repair_for`, the one owner of repair texts; the registry held 6 rows with a
     repair at the base and holds 13 with this Change.
   - **Considered:** a table of next steps in the application module, as the Attestation commands
     keep.
   - **Chosen because:** a second table restates what the registry owns. A transition gap without
     a registered repair gets one general instruction.
   - **Applies to:** the seven new codes. The step is an instruction, since each repair is an
     installation, a tag, a file or a writable store that no single ETHOS command provides.
10. **The break is the product's alone, and the reader already shipped.**
    - **Rests on:** the first half's decision 8 and its reader, released in 0.2.0-beta.11.
    - **Considered:** holding the writer one more release, which delays the first accepted
      identity past the first rehearsed release.
    - **Chosen because:** the only repository that records an identity is the product's. After
      its first applied acceptance, an engine older than 0.2.0-beta.11 refuses the set with
      `accepted_release_attestation_invalid`, so its runtime rolls back no further than that
      release. A governed repository records no identity and reads none.
    - **Applies to:** the product repository's Attestation set. The changelog entry states it.

## Risks / Trade-offs

- No test runs a real installed release. The tests replace the installation reader and its wheel
  with a wheel that carries a build identity; the first real run is this release's own acceptance,
  a preview and then an apply (the lane tasks). A development build names no release, and the
  previous release does not carry the operation.
- The binding compares the installed wheel with the checksum file by file name. A platform whose
  wheel the release does not publish refuses with `accepted_release_checksum_mismatch`. One
  platform of one release was read (decision 4).
- The operation trusts the checksum file it is given. The guide tells the operator to verify the
  file's attestation first.
- An accepted identity is immutable. A fault found after the apply needs a later release; the undo
  that the guide states, reinstalling the predecessor, belongs before the apply.
- The publish refusal covers one repository. Until `release-ref-policy-report` lands, a governed
  repository's tag publishes without its release policy being read, as today.
- The publish refusal reads the checkout. A release tag that names an earlier commit than the
  checkout's head is judged by the checkout's tree, as the repository audit is. Reading the
  tagged tree needs the report's readers to take a commit, which no Change does yet; refusing
  a tag that the checkout does not name would end the publication of an earlier tag, which the
  proof selection supports.
- The hand-kept operation count in the catalog test moves from 107 to 109 here; two other Changes
  of the batch each add one operation, so the stack's count is theirs to merge.
