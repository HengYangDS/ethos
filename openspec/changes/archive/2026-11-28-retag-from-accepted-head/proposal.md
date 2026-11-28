# Proposal

## Why

After a completed signature repair, `ethos land --retag` re-creates each release tag on the
commit that the repair mapped its target to. Its apply moved a tag only when the asking checkout's
head was that mapped commit; its preview answered ready from any checkout. So a batch whose tags
map to different commits moved and receipted the first tag and then raised
`git_effect_plan_prestate_stale` on the next, and no one checkout could re-create both. The
accepted branch's head, where a release lead stands after a repair, could re-create only a tag
whose mapped commit was that head itself.

A checkout with no commit shows the same split between preview and apply, recorded as the known
defect `retag-preview-ready-on-unborn-checkout`: its preview answers `ready_to_retag`, and the apply
is then refused by the plan's pre-state check, with no cause and no step named.

## What Changes

- A tag is planned when the asking checkout's head is its mapped commit, or is the accepted
  branch's head with the mapped commit among its ancestors. Any other checkout refuses that tag
  with `release_retag_checkout_unrelated`. The preview and the apply run the same plan, so they
  agree.
- A batch asked from the accepted head over tags on different commits is planned and applied under
  one plan digest.
- The known defect `retag-preview-ready-on-unborn-checkout` is repaired: an unborn checkout is
  refused at the preview.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: gains the requirement "A release tag is re-created from its repaired
  line".

## Impact

- Code: `src/ethos/adapters/mutation/accepted/retag.py`; tests in
  `tests/unit/cli/land/publication/test_mapped_retag.py`.
- Specification: `repository-governance` gains the requirement "A release tag is re-created from
  its repaired line"; the accepted requirements on re-created tags are unchanged.
- Where a tag lands does not change: the completed repair's mapping, the signature and the request
  decide it, as before.
