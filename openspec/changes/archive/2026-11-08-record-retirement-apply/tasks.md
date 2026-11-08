# Tasks

## 1. Apply

- [x] 1.1 Restore tombstones before any scan. Done when a test shows an interrupted apply's
      tombstones restored by the next preview, a re-created name kept beside its tombstone, and a
      rerun deleting the rest of a half-deleted lane unit with its receipt last. Evidence:
      `test_an_interrupted_apply_is_restored_first_and_then_continued` and `test_tombstones.py`
      passed in the impacted-test runs at 0aa061579 (4,592 passed 17:19:30 to 18:04:33 before the
      2,700 s bound, one architecture check failing until its detector fix f73ac7f5a; the 1,105 not
      yet reached passed 18:10:23 to 18:17:24) and the 189 direct tests on the tree committed as
      89d15760f (98 % branch coverage of the changed modules, 18:32:34 to 18:32:55).
- [x] 1.2 Delete only plan items a fresh scan still selects. Done when a test shows a changed, young
      or newly named item kept, an absent planned file counted as done, and a schema-1 plan refused.
      Evidence: `test_an_item_that_changed_or_is_named_since_its_plan_stays` (touched, named,
      member, absent, floor) and the schema-1 case of `test_an_apply_refuses_and_deletes_nothing`
      passed in the same runs.
- [x] 1.3 Defer on another ETHOS interpreter of the repository. Done when a test shows a batch
      deferred by a non-selected runtime's process and by an unreadable listing, and not by another
      repository's process, a hook run or a shell naming a `.venv`. Evidence:
      `test_another_interpreter_of_the_repository_defers_the_batch` (generation, unknown, elsewhere)
      and `test_writers.py` (another repository, a hook run, a shell naming a `.venv`) passed in the
      same runs.
- [x] 1.4 Compare under the custody lock. Done when a test shows a set swap or an accepted advance
      during the compare restoring what it names, a held custody lock deferring the batch, and a
      custody-free swap waiting for the lock. Evidence:
      `test_a_move_during_the_compare_keeps_what_it_names` (accepted, member, held) and
      `test_a_swap_without_custody_waits_for_a_held_custody_lock` passed in the same runs, with the
      87 Attestation set tests.
- [x] 1.5 Receipt each run. Done when a test shows the receipt's per-kind counts and reasons, the
      live-token fact, and a plan with a deferral-free receipt deleting nothing. Evidence:
      `test_an_apply_deletes_its_plan_once_and_receipts_the_run` (per-kind counts, the live-member
      fact, `already_applied` on a rerun) passed in the same runs.
- [x] 1.6 Re-link adopted records. Done when tests show a writer restoring a record renamed away
      before its read and after it. Evidence: the re-link cases of
      `tests/unit/adapters/store/test_content_addressed.py`, renamed away before and after the read,
      passed in the same runs.

## 2. Command

- [x] 2.1 Expose the apply. Done when the preview's `next` names the destructive apply, and an apply
      without `--authorize` or `--expect-plan`, or with `retention.lock` held, refuses and deletes
      nothing. Evidence: `tests/unit/cli/test_hook_record_retirement.py` (the preview's destructive
      `next`, a refused apply without `--authorize`, the apply), the `_DESTRUCTIVE` row in
      `test_result_next_step.py` and the refusal table of `test_apply.py` passed in the same runs.
- [x] 2.2 Correct the docs. Done when the command reference and the local-state architecture
      describe the apply. Evidence: `docs/reference/command-plane.md` and
      `docs/architecture/local-state.md` describe the apply at 0aa061579, and Prettier and Vale
      passed at its commit.

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck's static checks passed at 89d15760f (18:34:31 to 18:34:37), its
      impacted tests as recorded in task 1.1, and readiness passed 28 gates at 89d15760f with the 6
      heavy gates left to the proof (18:35:54).
