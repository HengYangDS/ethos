# Tasks

## 1. Behaviour

- [ ] 1.1 Report what a clone knows about its peers. Done when `test_peer_feed.py` shows an invalid
      declaration's gaps alone, an unread declared peer before an empty feed, a forge-key-only, an
      emptied and a hostless remote, and an undeclared `forgePrivate` remote that feeds, and the
      `status` tests pass unchanged.
- [ ] 1.2 Refuse an unknown feed under `required`. Done when `test_peer_identity_push.py`, its
      fixture holding both declared peers' remotes, refuses an unread peer and an empty feed without
      reading an advertisement and passes them under `disabled` and on a deletion, and a
      `push_admission_report` test shows `peer_identity_refused` as the reason of a push that only
      a feed gap blocks.
- [ ] 1.3 Answer `unknown` in the redaction verb. Done when `test_lane_redaction.py`, its fixture
      holding both declared peers' remotes, shows the preview, the apply and the verify answering
      `unknown` with the gap before a key is validated, the apply writing nothing and the verify
      recording no Attestation.

## 2. Documentation

- [ ] 2.1 Name the rule for operators. Done when the redaction and push-check paragraphs of
      `docs/reference/operational-roots.md` and the two Unreleased CHANGELOG entries state it.

## 3. Acceptance

- [ ] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
