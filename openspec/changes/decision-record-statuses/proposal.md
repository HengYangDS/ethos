# Proposal

## Why

The decision-record form, which `decision-record-form` lands as text and DR-0031 records, gives a
record four statuses: accepted, superseded, deprecated and rejected. Every released engine
refuses each status but accepted and each state but canonical for a decision record, and it
asks the five sections of every record. So the form's second step waits for the engine: a
superseded record cannot say so in its status, a rejected ruling cannot be kept, and the seven
records that this repository removed on 2026-08-15 cannot come back.

A patch on the head that 0.2.0-beta.11 tags was prepared on 2026-11-19 and is not in this lane:

- The validator of decision records accepts the four statuses. A superseded record must name
  its successor in its relations. The five sections bind a record in force, accepted or
  rejected; a record that no longer governs keeps the sections it has. The title, the name, the
  identity and the rule against execution content bind every record.
- New cases for it were written first; six of them fail on the released behavior. With the
  change, the module and its two neighbours pass, 123 cases.
- A trial restored the seven removed records from Git in the form. Under the changed validator
  the documentation registry passes with all seven, and after the formatter's pass the Markdown
  lint and the prose gate pass. 8 of their 32 local links name paths that no longer exist, so a
  record's return includes the repair of its links.

## What Changes

Candidates for this row, none built in this lane:

- The validator's widening as prepared. It refuses nothing that passes today.
- The requirement's scenario on status and state, which today names accepted and canonical
  alone, changes with it.
- Not in this row: a check of the banner, of the relations' two sides and of the index's rows,
  and the index written by the product. They follow 0.2.0 as reports before any of them refuses.

It is no row of the release candidate gate. Before 0.2.0 a weekly batch carries one row outside
the gate, and the next batch's place is taken, so this row waits for the first batch whose place
is free. Not sized on this lane's tree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None yet. The row modifies the requirement on decision rationale in `repository-governance`;
this draft carries no delta, so `skip_specs: true` applies.

## Impact

The registry's validator of decision records and its tests. A repository that writes a status
other than accepted afterwards needs this engine or a later one, which the form's text already
states.
