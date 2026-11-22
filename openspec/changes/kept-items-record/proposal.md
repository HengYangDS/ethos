# Proposal

## Why

The owner's rule of 2026-11-20 and 2026-11-21: keeping an item aside without absorbing it piles up
waste; kept things may only decrease; and what a higher form has absorbed, covered or corrected
need not be kept, once that is established before the deletion.

On 2026-11-21 this repository held 15 kept refs, none made by the product. For five of them the
precondition is established: the accepted history holds the content of every one of their
commits. The owner approved their deletion on 2026-11-21, to follow a landed record that names
each ref. Three more have a consumer, the product itself. Seven are not decided.

## What Changes

- DR-0034 records the rule, the five refs that leave with the evidence for each, the three that
  stay with their consumer, and the seven that it does not decide.
- The decisions index gains its row.

Not here: the deletions, which follow the landing after the precondition is read again in that
hour; and a product function that enforces the rule, which would be a new rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement changes, so `skip_specs: true` applies.

## Impact

`docs/decisions/` (one record and the index). No command, schema or verdict changes.
