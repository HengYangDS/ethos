# Tasks

## 1. Grammar and feed

- [x] 1.1 Implement the shared grammar. Done when vector tests cover each kind over a neighbour
      grid, the pre-image field order and NUL joins, the key reader's refusals, numeric replacement
      that never equals a fed value or the original and never `0`, exhaustion, the closed contexts
      and the boundaries, and `replacement_spans` returns `manual` for an unclassified occurrence.
      Evidence: at cf82d97c7 `tests/unit/repository/test_paradigm_peer_identity.py` holds the form
      table with the fed path boundaries (`test_each_occurrence_takes_one_form`), the 35-case host
      neighbour grid (`test_each_neighbourhood_yields_exactly_one_host_form`), a known-answer marker
      over the versioned, NUL-joined pre-image
      (`test_markers_are_keyed_canonical_and_distinct_per_shape`), the key reader's four refusals,
      numbers that avoid the original, the fed values and the domain and exhaust, and `manual` for
      an unclassified occurrence; they passed in the impacted sweep (6,446 impacted tests in two
      runs from the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to 01:12:46,
      and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).
- [x] 1.2 Read the feed from local Git state. Done when a fixture repository's peers yield their
      hosts, ports, paths, project IDs and former values, and no result or error carries a value.
      Evidence: at cf82d97c7 `test_the_feed_reads_protected_peers_and_their_former_values` reads a
      private-class peer's hosts, ports, paths, project IDs and former values and a public peer's
      once opted in, `test_a_repository_without_peers_feeds_nothing` feeds nothing, and the verb's
      tests assert that no output carries the host or the project ID; they passed (6,446 impacted
      tests in two runs from the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to
      01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).
- [x] 1.3 Bind `record_roots`. Done when a profile with directories validates, a file path is
      `repository_profile_invalid`, and the effective roots add them to the immutable roots.
      Evidence: at cf82d97c7 `test_record_roots_extend_the_effective_roots` admits a directory,
      which joins the effective roots, and reads a file path as `repository_profile_invalid`; it
      passed (6,446 impacted tests in two runs from the lane root: 3,082 passed and 2 skipped at
      956830a16 from 00:22:57 to 01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).

## 2. Verb

- [x] 2.1 Preview without a key. Done when the preview lists file, line, form and root membership
      for each occurrence in a fixture's tracked tree, counts those outside the effective roots, and
      prints no value. Evidence: at cf82d97c7 `test_a_redaction_is_previewed_applied_and_verified`
      previews 4 occurrences, 1 outside the effective roots, without printing a value, and its
      fixture's binary and non-UTF-8 files are never read; it passed (6,446 impacted tests in two
      runs from the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to 01:12:46,
      and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).
- [x] 2.2 Apply under prewrite and the Lease. Done when an authorized apply at the lane head writes
      markers and numbers in the effective roots only, a stale head or a `manual` occurrence refuses
      and writes nothing, and the digest a record in the same commit holds follows its file.
      Evidence: at cf82d97c7 the same test applies at the lane head and changes only the record and
      the index that holds its digest; `test_an_apply_refuses_and_writes_nothing` refuses a missing
      authorization, a stale head, an unusable key and a manual occurrence, and
      `test_an_apply_proves_each_step_and_never_overwrites` covers nothing to redact, a preimage
      moved before and after admission, a refused admission, a failed apply and a digest cycle; they
      passed (6,446 impacted tests in two runs from the lane root: 3,082 passed and 2 skipped at
      956830a16 from 00:22:57 to 01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).
- [x] 2.3 Verify and record. Done when `--verify` re-derives every marker and number from the base
      and records `redaction:private-peer` with base, head, roots, count and key generation, a
      missing base is `unknown`, and another generation refuses without `--rotate`. Evidence: at
      cf82d97c7 the same test verifies with count 3 and reads the recorded Attestation's base, head,
      roots, count and generation back, refuses another key with `redaction_key_generation_changed`
      and reads a missing base as `unknown`; `test_a_verify_refuses_a_head_its_base_does_not_derive`
      refuses an edited head and an empty base; they passed (6,446 impacted tests in two runs from
      the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to 01:12:46, and 3,362
      passed at 732d0ae7a from 01:15:50 to 01:59:01).

## 3. Markers

- [x] 3.1 Accept the peer marker in the content scans. Done when content holding a marker passes the
      scans and the bracket marker's pins are gone from the specification and test support.
      Evidence: at cf82d97c7 the test support's `redaction` documentation text carries the peer
      marker through `test_message_admission_reads_classes_not_names` and
      `test_native_scan_gives_the_same_verdict_per_line`, the spec delta replaces the bracket
      marker's scenario, and no specification or test support names it; they passed (6,446 impacted
      tests in two runs from the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to
      01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).

## 4. Acceptance

- [x] 4.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the static precheck passed at cf82d97c7 (02:01:45), the impacted sweep passed
      (6,446 impacted tests in two runs from the lane root: 3,082 passed and 2 skipped at 956830a16
      from 00:22:57 to 01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01), and
      readiness passed 28 gates at cf82d97c7 (02:04:36), with the 6 heavy gates left to the proof.
