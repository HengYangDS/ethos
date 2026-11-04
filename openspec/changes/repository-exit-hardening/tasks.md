# Tasks

## 1. Ownership and record

- [x] 1.1 Decide ownership per key at the record owner, including legacy hooks paths, and record
      only values that ETHOS does not own. Re-adoption updates stale entries and clears an earlier
      receipt. Done when tests show a legacy worktree hooks path never recorded, a re-adoption
      after a hooks change recording the new value, and an upgrade leaving the record
      byte-identical. Evidence: `test_exit_ownership.py`.
- [x] 1.2 Write records and receipts durably. Done when a test shows the file and its directory
      synced before the replacement is reported. Evidence: `test_durable.py`.

## 2. Plan

- [x] 2.1 Compute the after state per key with kept, left and unrestorable entries, and the
      generation plan, all in the digest. Done when tests show a hooks path set after adoption
      kept, a linked worktree's recorded value restored, unrecorded ref-storage keys left and
      reported, and the apply removing exactly the planned generations while keeping one in use.
      Evidence: `test_exit_ownership.py`, `test_exit_apply.py`.
- [x] 2.2 Exclude the exit's own process, include the installed runtime a selector names, and read
      an unreadable process as unknown. Done when tests show each case. Evidence: `test_exit.py`,
      `test_retirement_listing.py`.
- [x] 2.3 Name the exact decision for an unrecorded hooks path. Done when a test shows the Git
      commands in the next action. Evidence: `test_exit_ownership.py`.

## 3. Apply

- [x] 3.1 Fence the apply with a state write transaction, and compare each key and selector with
      its planned value before writing it. Done when tests show a concurrent change refused
      without loss, blockers that appear after the preview refusing the apply, and a busy lock
      reported as a gap. Evidence: `test_exit_apply.py`, `test_config_effects.py`.
- [x] 3.2 Remove the record first, mark the receipt applied inside the fence, and resume an
      applying receipt. Done when tests show an interruption after each step resumed to an
      applied exit, status reporting an interrupted receipt, and a re-adoption after an exit.
      Evidence: `test_exit_resume.py`.
- [x] 3.3 Attempt every compensation step and report the failures. Done when tests show
      compensation after a configuration write failure and after a failed verification, and an
      `unknown` result when compensation itself fails. Evidence: `test_exit_apply.py`; a mutant
      of each rule fails its test.

## 4. Surfaces

- [x] 4.1 Exercise the exit through MCP, and update the `runtime-activation` delta and the command
      reference. Done when the MCP test passes and strict validation and the cumulative archive
      simulation pass. Evidence: `test_adopt_exit.py`; both pass after each commit.
