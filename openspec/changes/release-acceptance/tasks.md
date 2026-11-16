# Tasks

## 1. Publish refusal

- [ ] 1.1 Add `is_product_root` and `release_ref_policy` to the release configuration. Done when a
      root that declares the product profile reports the policy's gaps with a next step for the
      release tag role, any other role or root passes, and the product tree reports none
      (`tests/unit/release/test_release_acceptance.py`).
- [ ] 1.2 Read the report in `observe_publication` and name its step in
      `blocked_publication_action`. Done when a publication of a release tag blocks with the
      policy's gap and its next step, and the publication tests that passed before still pass.
- [ ] 1.3 Print the policy report in the publication result and state the tree it reads. Done
      when a blocked release-tag publication carries the report under `data.release_policy`,
      and the design, the delta and the release guide say that the report reads the checkout.
- [ ] 1.4 Raise the profile's own gap from `is_product_root` for a profile that cannot be read.
      Done when `release accept` in such a root refuses with `repository_profile_invalid:<path>`.
- [ ] 1.5 Read the product tree's own policy once, from the root that holds the test. Done when
      that test passes from any working directory.

## 2. The operation

- [ ] 2.1 Split `admit_explicit_release` from `materialize_explicit_release`. Done when the
      admission returns the identity and whether the set holds it, with no effect, and
      `tests/unit/release/test_runtime_transition.py` passes unchanged.
- [ ] 2.2 Declare `release accept` and the hidden group `release` in the catalog, map it to its
      implementation, and keep it in the invoking installation. Done when the catalog test counts
      109 operations, the argv `release accept --checksums <file> --apply` selects
      `release.accept.apply`, and the console runs the command without reading `CURRENT`.
- [ ] 2.3 Implement the acceptance in `src/ethos/application/land/release_acceptance.py`. Done when
      each refusal of the delta leaves the Attestation set and the package store untouched and
      names its registered repair, a passing preview names the apply with the checksum file's
      absolute path, the apply records one identity of payload version 3, and a second run reads
      `unchanged` with the same set root and the same stored file.
- [ ] 2.4 Register the six new gap codes with their repairs. Done when
      `tests/architecture/test_gap_registry.py` passes.
- [ ] 2.5 Have admission answer with the recorded identity, and report it. Done when a version
      recorded without the binding reads `unchanged` with the recorded identity on a preview
      and on an apply that presents the checksum file, and the set does not change.
- [ ] 2.6 Restore the transition's exact Attestation check and read the wheel once. Done when a
      record that another writer made refuses with `identity_transition_attestation_mismatch`,
      and a wheel that changes after it was read is stored with the admitted bytes.
- [ ] 2.7 Name a failed store or Attestation write by its own registered code. Done when a
      write that meets `ENOSPC` refuses with `release_acceptance_store_unavailable:ENOSPC` and
      the registry row's repair.
- [ ] 2.8 Order the installed and the committed version as SemVer texts. Done when a committed
      version outside the wheel profile refuses as older or newer, by a registered code.

## 3. Documents

- [ ] 3.1 Describe the operation in `docs/reference/operational-roots.md`, name the hidden root in
      `docs/reference/command-plane.md`, and add the acceptance step and the undo to step 5 of the
      release guide. Done when the registered-root test, the carried-document tests and Prettier
      pass on the three pages.
- [ ] 3.2 Add the CHANGELOG entry with the consequence for a rollback of the product repository.
      Done when the entry sits under Unreleased and passes Prettier.

## 4. Lane tasks

- [ ] 4.1 Apply after `command-reference-split`, and merge the hand-kept operation count with the
      other Changes of the batch that add operations. Done when the catalog test passes on the
      stack with the stack's count.
- [ ] 4.2 Measure the three source budgets on the lane head and record the deltas with their
      reason. Done when the figures are in this task.
- [ ] 4.3 Run the prose gate on the changed pages and the Change documents. Done when Vale and
      codespell pass.
- [ ] 4.4 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.
- [ ] 4.5 Accept this release on the releasing host after its journey passes: install it as the
      global `ethos`, verify the attestation of `SHA256SUMS`, run the preview, then the apply. Done
      when the apply reads `accepted`, a second run reads `unchanged`, and the release Change
      records both results. It is the operation's first real run: a development build names no
      release, and the previous release does not carry the operation.

## Workflow follow-up

- The draft Change `release-ref-policy-report` carries the governed-repository form of the publish
  refusal: one release reports the gaps before any refusal.
- The requirement `Release Policy` of the repository-governance specification still names
  `ethos publish --json` and retired command owners; its review is not part of this Change.
