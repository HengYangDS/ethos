# Tasks

## 1. Publish refusal

- [x] 1.1 Add `is_product_root` and `release_ref_policy` to the release configuration. Done when a
      root that declares the product profile reports the policy's gaps with a next step for the
      release tag role, any other role or root passes, and the product tree reports none
      (`tests/unit/release/test_release_acceptance.py`).
- [x] 1.2 Read the report in `observe_publication` and name its step in
      `blocked_publication_action`. Done when a publication of a release tag blocks with the
      policy's gap and its next step, and the publication tests that passed before still pass.
- [x] 1.3 Print the policy report in the publication result and state the tree it reads. Done
      when a blocked release-tag publication carries the report under `data.release_policy`,
      and the design, the delta and the release guide say that the report reads the checkout.
- [x] 1.4 Raise the profile's own gap from `is_product_root` for a profile that cannot be read.
      Done when `release accept` in such a root refuses with `repository_profile_invalid:<path>`.
- [x] 1.5 Read the product tree's own policy once, from the root that holds the test. Done when
      that test passes from any working directory.

## 2. The operation

- [x] 2.1 Split `admit_explicit_release` from `materialize_explicit_release`. Done when the
      admission returns the identity and whether the set holds it, with no effect, and
      `tests/unit/release/test_runtime_transition.py` passes with the six cases that
      `test_release_transition_attests_only_after_matching_post_observation` held at the base
      expecting what they expected there.
- [x] 2.2 Declare `release accept` and the hidden group `release` in the catalog, map it to its
      implementation, and keep it in the invoking installation. Done when the catalog test counts
      the batch's 111 operations, of which this Change adds two to the base's 107, the argv
      `release accept --checksums <file> --apply` selects `release.accept.apply`, and the console
      runs the command without reading `CURRENT`.
- [x] 2.3 Implement the acceptance in `src/ethos/application/land/release_acceptance.py`. Done when
      each refusal of the delta leaves the Attestation set and the package store untouched and
      names its registered repair, a passing preview names the apply with the checksum file's
      absolute path, the apply records one identity of payload version 3, and a second run reads
      `unchanged` with the same set root and the same stored file.
- [x] 2.4 Register the six new gap codes with their repairs. Done when
      `tests/architecture/test_gap_registry.py` passes.
- [x] 2.5 Have admission answer with the recorded identity, and report it. Done when a version
      recorded without the binding reads `unchanged` with the recorded identity on a preview
      and on an apply that presents the checksum file, and the set does not change.
- [x] 2.6 Restore the transition's exact Attestation check and read the wheel once. Done when a
      record that another writer made refuses with `identity_transition_attestation_mismatch`,
      and a wheel that changes after it was read is stored with the admitted bytes.
- [x] 2.7 Name a failed store or Attestation write by its own registered code. Done when a
      write that meets `ENOSPC` refuses with `release_acceptance_store_unavailable:ENOSPC` and
      the registry row's repair.
- [x] 2.8 Order the installed and the committed version as SemVer texts. Done when a committed
      version outside the wheel profile refuses as older or newer, by a registered code.
- [x] 2.9 Choose the standing record by the admission's own rule, and block on a refusal that
      carries no gap. Done when the five cases of `identities_agree` pass at its owner with the
      conflict that admission names for the two that disagree, a second checksum file of a recorded
      version refuses the transition and records nothing, and a refusal without a gap blocks under
      its class's name at each of the two sites of `release accept` that catch.

## 3. Documents

- [x] 3.1 Describe the operation in `docs/reference/operational-roots.md`, name the hidden root in
      `docs/reference/command-plane.md`, and add the acceptance step and the undo to step 5 of the
      release guide. Done when the registered-root test, the carried-document tests and Prettier
      pass on the three pages.
- [x] 3.2 Add the CHANGELOG entry with the consequence for a rollback of the product repository.
      Done when the entry sits under Unreleased and passes Prettier.

## 4. Lane tasks

- [x] 4.1 Apply after `command-reference-split`, and merge the hand-kept operation count with the
      other Changes of the batch that add operations. Done when the catalog test passes on the
      stack with the stack's count.
- [x] 4.2 Measure the three source budgets on the lane head and record the deltas with their
      reason. Done when the figures are in this task.
- [x] 4.3 Run the prose gate on the changed pages and the Change documents. Done when Vale and
      codespell pass.
- [x] 4.4 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head. Both passed at `4a5029e96` on 2026-11-17: the pre-check with 472 impacted test modules
      (9,555 passed, 5 skipped, no finding) and readiness with its 28 gates.
- [x] 4.5 Hand the operation's first real run to the release Change of this batch. Done when the
      Workflow follow-up names it: after the release's journey passes, the releasing host installs
      the release as the global `ethos`, verifies the attestation of `SHA256SUMS`, runs the preview
      and then the apply, and the release Change records that the apply reads `accepted` and a
      second run reads `unchanged`.

## Workflow follow-up

- The draft Change `release-ref-policy-report` carries the governed-repository form of the publish
  refusal: one release reports the gaps before any refusal.
- The requirement `Release Policy` of the repository-governance specification still names
  `ethos publish --json` and retired command owners; its review is not part of this Change.
- Release: after the journey of 0.2.0-beta.12 passes, accept the release on the releasing host
  (install it as the global `ethos`, verify the attestation of `SHA256SUMS`, preview, then apply)
  and record in the release Change that the apply reads `accepted` and a second run reads
  `unchanged`. It is the operation's first real run: a development build names no release, and the
  previous release does not carry the operation.
