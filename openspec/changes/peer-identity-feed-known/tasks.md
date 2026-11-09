# Tasks

## 1. Behaviour

- [x] 1.1 Report what a clone knows about its peers. Done when `test_peer_feed.py` shows an invalid
      declaration's gaps alone, an unread declared peer before an empty feed, a forge-key-only, an
      emptied and a hostless remote, and an undeclared `forgePrivate` remote that feeds, and the
      `status` tests pass unchanged. Evidence: at d505a4e8d
      `test_the_reader_names_what_the_clone_cannot_know` covers the complete, unread, keys-only,
      emptied, hostless and invalid cases, with the undeclared marked mirror feeding in every case
      but the unmarked hostless one; it failed with an ImportError before the change (09:41:45 to
      09:42:00, uncommitted on 149c410b9) and passes after it (50 passed, 09:43:07 to 09:43:22), and
      the two `status` tests of `test_peer_identity_push.py` pass unchanged; the impacted sweep at
      a7bbbef8d passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to 10:30:24).
- [x] 1.2 Refuse an unknown feed under `required`. Done when `test_peer_identity_push.py`, its
      fixture holding both declared peers' remotes, refuses an unread peer and an empty feed without
      reading an advertisement and passes them under `disabled` and on a deletion, and a
      `push_admission_report` test shows `peer_identity_refused` as the reason of a push that only a
      feed gap blocks. Evidence:
      `test_a_feed_the_clone_cannot_know_refuses_before_the_advertisement` (unread and unfed, with
      the peer unreachable) and `test_a_push_that_only_peer_identity_blocks_names_its_reason` failed
      before the change and pass after it in the same runs, and the disabled, invalid and deleted
      rows of `test_the_mode_decides_whether_a_push_is_read` pass; the impacted sweep at a7bbbef8d
      passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to 10:30:24).
- [x] 1.3 Answer `unknown` in the redaction verb. Done when `test_lane_redaction.py`, its fixture
      holding both declared peers' remotes, shows the preview, the apply and the verify answering
      `unknown` with the gap before a key is validated, the apply writing nothing and the verify
      recording no Attestation. Evidence: `test_every_mode_answers_unknown_without_a_known_feed` and
      the `unfed` case of `test_an_apply_proves_each_step_and_never_overwrites` failed before the
      change and pass after it in the same runs; the impacted sweep at a7bbbef8d passed (359 files:
      6,988 passed and 2 skipped, 09:50:47 to 10:30:24).

## 2. Documentation

- [x] 2.1 Name the rule for operators. Done when the redaction and push-check paragraphs of
      `docs/reference/operational-roots.md` and the two Unreleased CHANGELOG entries state it.
      Evidence: d505a4e8d adds the paragraph that follows the redaction and push-check paragraphs of
      `docs/reference/operational-roots.md`, and the feed gaps to the redaction and push-check
      entries of the Unreleased CHANGELOG.

## 3. Acceptance

- [x] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. Evidence: at a7bbbef8d the static precheck passed with no finding over 41
      changed files (09:51:36 to 09:51:42), readiness passed 28 gates (09:49:09 to 09:50:00) and the
      impacted sweep at a7bbbef8d passed (359 files: 6,988 passed and 2 skipped, 09:50:47 to
      10:30:24).
