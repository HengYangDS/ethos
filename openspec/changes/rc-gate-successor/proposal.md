# Proposal

## Why

DR-0026 records the release candidate's gate and sets the candidate for 2026-12-19. On 2026-11-14 a
committee of five seats signed one resolution that changes that gate. It adds the one item the gate
lacked, a declared state for every rule that can block. It withdraws 2026-12-19, and it states the
rules a batch lands by, the slip rule and the measures the owner reads each week. The owner
approved a successor record that day, on the condition of reading its whole text by the cut of
2026-11-19, and approved the text as drafted on 2026-11-15.

Until the record lands, the resolution is one session's local document, and the tracked tree knows
the candidate's date through DR-0026 alone.

## What Changes

- DR-0029 is added with the approved text and indexed in the decisions README. It succeeds DR-0026
  and does not edit it.

Not breaking: one decision record and its index line. No command, schema or rule changes; the rule
of the record that the product enforces arrived with the `reporting-obligations` Change.

The terminal plan's paragraph on the release candidate keeps its text. What it says of DR-0026, the
gate and its waivers, still stands, and the plan is at its bound of 500 lines; the decisions README
is the navigation to a successor.

The number 0028 stays held for the test budget step that the same resolution numbers. A decision
number is an identity and is never reused, so the later record fills it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement changes, so `skip_specs: true` applies.

## Impact

`docs/decisions/dr-0029-release-candidate-gate-successor.md` and `docs/decisions/README.md`.
