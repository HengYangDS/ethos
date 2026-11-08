# Proposal

## Why

`ethos hook retire-records` plans the store records that may retire but deletes nothing. On
2026-11-08 its plan over ETHOS's own store held 1,380 items and 5,059,593,399 bytes: lane retirement
units, proof-check documents, gate attempt archives and a merge preimage. This Change adds the apply
that deletes them, the one deleting step of store retention in the archived `rc-plan` (Appendix D),
with recovery at every point and the rechecks its four design reviews required.

## What Changes

- `ethos hook retire-records --expect-plan <digest> --apply --authorize --json` applies one plan;
  the preview names it as `next` when the plan has candidates, and admission reports it as a
  destructive step.
- Recovery first: every preview and apply restores the tombstones an interrupted apply left, and a
  rerun of the same plan continues a half-deleted lane unit; each run writes one receipt.
- The apply deletes only what a fresh scan still selects and the plan names, judged per item, and
  keeps one token set for the whole run. Plans become schema 2 with store-relative paths.
- A batch defers while another ETHOS interpreter of the repository runs: another runtime generation,
  an installation the repository uses or one of its worktrees' environments.
- The custody compare decodes outside the custody lock and unlinks inside it; every Attestation set
  swap now takes the custody lock.
- A content-addressed write links its bytes again when its name vanished during an apply.
- The command reference and the local-state architecture stop saying the verb deletes nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: store records retire only through an allowlisted write-ahead plan; the
  requirement adds the apply.

## Impact

- `src/ethos/application/retention.py` and new `src/ethos/adapters/store/retention/` modules for
  tombstones, the writer check and the apply; `src/ethos/adapters/repo/attestation_set.py`
  (`_custody_guard`), `src/ethos/adapters/store/content_addressed.py`,
  `src/ethos/surface/cli/hook/commands.py`, `src/ethos/contracts/admission.py`, and the docs.
- Tests on fixture stores with child processes or injected hooks, never sleeps.
- Not here: publication requests and superseded lane units (`record-retirement-kinds`), and the
  retention of plans and receipts.
