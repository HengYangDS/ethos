# Proposal

## Why

An independent safety review of `repository-exit` and `repository-exit-apply` found that the exit
can damage what a repository owns:

- It restores keys that ETHOS no longer owns, so a hooks path set after adoption, such as Husky's,
  is unset by the exit.
- An interrupted exit cannot resume, and its leftover record blocks the next adoption.
- Compensation stops at its first failure, the receipt is not durable, and the `applied` mark sits
  outside the fence.
- A Lease can be taken between the exit's check and its effects.
- The record can hold ETHOS's own legacy hooks path as if it were the user's.
- The preview and the apply can disagree, and process detection has gaps.

## What Changes

- Ownership is decided per key, at one owner. A key is ETHOS's while it holds ETHOS's activation
  value or an ETHOS hooks path, current or legacy. Install records only values that ETHOS does not
  own, keeps the entry of a key it already owns, updates stale entries on re-adoption, and clears
  an earlier exit's receipt.
- The preview computes the configuration after the exit per key, the keys it keeps, the keys it
  leaves unrecorded, the record entries it cannot restore, and the generations it removes, and
  binds them all in the digest. It resumes an interrupted exit from its receipt.
- The apply holds a state write transaction beside the selection lock, so no Lease can start
  inside the fence. It removes the record first and writes each key and selector only while they
  hold their planned values. Its receipt is durable, and its `applied` mark is inside the fence.
  Compensation attempts every step and reports the steps that fail.
- Process detection excludes the exit's own process, includes the installed runtime that a
  selector names, and reads a process whose command line is unreadable as unknown.
- An unrecorded hooks path names the exact Git commands that settle it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: the record, the exit's preview, blockers and apply, and status after an
  exit.

## Impact

- `src/ethos/adapters/repo/hook/`: `preimage.py`, `exit_plan.py` (new, the plan split from
  `exit.py`), `exit.py`, `activation.py` and `observation.py`.
- `src/ethos/adapters/repo/config_effects.py`, `src/ethos/adapters/repo/runtime/retirement.py`,
  `src/ethos/adapters/process.py` and `src/ethos/adapters/store/durable.py` (new).
- The hook, retirement and process tests, and the command reference.
