# Proposal

## Why

The owner directed on 2026-11-13 that supply moves at a release age of 0 hours. It holds today by
declaration: each governed repository on the releasing host declares the age in its own toolchain
settings. Two readers of that declaration are not built: the supply refresh does not read it, and
`status` does not show it. Their absence blocks nothing today.

The release lead ruled on 2026-11-15, among the rows that no order holds, that this work takes a
weekly off-gate slot only when one is free at a cut, behind the removal of archived names, and
otherwise follows 0.2.0.

## What Changes

- The refresh reads the declared release age.
- `status` shows it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The supply refresh and the status reader. It adds no rule.

Owner: the release lead. Next action: none before a free slot. Read again: after 0.2.0.
