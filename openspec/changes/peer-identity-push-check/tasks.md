# Tasks

## 1. Checks

- [x] 1.1 Refuse what a push adds. Done when a test shows a fed host in an added line and in a
      message refused by form and position, the same content refused nothing once the peer
      advertises it, a disabled or unread mode reading nothing, an unreadable peer `unknown` and a
      deletion reading nothing. Evidence: at cf82d97c7
      `test_a_push_refuses_the_identity_it_adds_and_only_that` refuses a fed host in an added line
      and in a message by form and position and nothing once the peer advertises it;
      `test_the_mode_decides_whether_a_push_is_read` reads nothing under `disabled`, an unread mode
      (`peer_identity_mode_unread`), an unfed peer or a deletion; and
      `test_the_advertisement_bounds_what_a_push_adds` reads an unreachable peer as
      `peer_identity_range_unknown:gitlab` and the tracking view, a peer without tips and a tag
      message as the network does; they passed (6,446 impacted tests in two runs from the lane root:
      3,082 passed and 2 skipped at 956830a16 from 00:22:57 to 01:12:46, and 3,362 passed at
      732d0ae7a from 01:15:50 to 01:59:01).
- [x] 1.2 Backstop raw pushes in CI. Done when a test shows the check inert without the job's
      variables, the missing-base advisory, a refusal under `required` and a pass under `disabled`,
      and the GitLab projection runs it after the policy step. Evidence: at cf82d97c7
      `test_the_ci_backstop_refuses_only_a_fed_literal_under_required` is inert without the job's
      variables, advises a missing baseline, refuses under `required` and passes under `disabled`,
      and `test_integration_events_transport_exact_commit_range_coordinates` requires the backstop
      as the GitLab commit-policy job's second step over the same coordinates and none on GitHub;
      they passed (6,446 impacted tests in two runs from the lane root: 3,082 passed and 2 skipped
      at 956830a16 from 00:22:57 to 01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to
      01:59:01).
- [x] 1.3 Verify marker edits without a key. Done when a test shows a redaction pairing, and a new
      marker file, changed words, an unkeyed and a malformed marker refusing, with markers outside
      the record roots ignored. Evidence: at cf82d97c7
      `test_a_marker_edit_pairs_with_what_it_replaced` pairs a redaction, refuses a new marker file
      and changed words (`record_marker_unpaired`), an unkeyed and a malformed marker and unread
      roots, and ignores markers outside the record roots, and `test_paradigm_marker_alignment.py`
      pairs every redacted line with its original; they passed (6,446 impacted tests in two runs
      from the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to 01:12:46, and
      3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).

## 2. Profile and status

- [x] 2.1 Bind the mode. Done when a profile with `[peer_identity] mode = "required"` validates, and
      `status` reports a protected peer under `disabled` and an unread mode as advisories. Evidence:
      at cf82d97c7 the push tests' profile with `[peer_identity] mode = "required"` validates and
      `test_the_mode_is_read_at_one_commit` reads it at a commit;
      `test_status_names_a_protected_peer_left_unchecked` advises a protected peer under `disabled`
      and an unread mode only, and
      `test_status_carries_the_advisory_in_its_summary_and_never_as_a_gap` reads it in
      `ethos status --json`'s `summary.peer_identity_advisories`; they passed (6,446 impacted tests
      in two runs from the lane root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to
      01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01).
- [x] 2.2 Repair wib's artifacts table. Done when the paradigm repair folds `[artifacts]` into
      `record_roots` on a fixture and plans nothing on a repaired tree. Evidence: at cf82d97c7
      `test_the_roots_move_to_the_profile_before_the_table_retires` declares
      `record_roots = ["evidence/"]` first, retires `[artifacts]` on the next repair and plans
      nothing on the repaired tree, and `test_an_invalid_root_is_reported_and_never_repaired` leaves
      five malformed roots report-only; they passed (6,446 impacted tests in two runs from the lane
      root: 3,082 passed and 2 skipped at 956830a16 from 00:22:57 to 01:12:46, and 3,362 passed at
      732d0ae7a from 01:15:50 to 01:59:01).

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the static precheck passed at cf82d97c7 (02:01:45), the impacted sweep passed
      (6,446 impacted tests in two runs from the lane root: 3,082 passed and 2 skipped at 956830a16
      from 00:22:57 to 01:12:46, and 3,362 passed at 732d0ae7a from 01:15:50 to 01:59:01), and
      readiness passed 28 gates at cf82d97c7 (02:04:36), with the 6 heavy gates left to the proof.
