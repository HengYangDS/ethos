# Proposal

## Why

The archived `rc-plan` design ends its sentence on the row `gate-environment` (Family 4, lines
101 to 104, R8(c)) with "and one owner redacts persisted failure output". The Change
`gate-environment` is that row's first slice, in 0.2.0-beta.13, and its design (Decision 9)
hands this half to a Change of its own, after `gate-child-environment`.

No owner masks what a gate printed. A search of the product for redaction finds peer identity
and the secret scan's own flag in 16 files, and nothing that reads a gate's output. The proof
operation and the proof artifact carry both streams of every check whole, as the accepted
requirement `Native command failures keep their complete outcome` asks. A declared command's
child receives every credential of its launch today, so a gate that prints its environment
writes those values into the proof's record.

The order matters. Masking by the values of variables whose names look like credentials would
rewrite evidence while every credential still reaches every child. Once
`gate-child-environment` builds the child from a list, a child can print only the variables
that its gate names, and one owner can mask exactly those values.

## What Changes

Candidates for this row's design, none decided:

- One owner masks, where the proof writes a check's record, the values of the variables that
  the check's gate named. The mask keeps the variable's name, so a reader sees which value was
  withheld.
- The requirement `Native command failures keep their complete outcome` is modified: complete,
  except for the named values.
- Whether the result that a command prints is masked as its record is, or only the record.
- A regression per carrier of a stream: the result, the proof artifact, the progress events and
  a provider's report.

Estimated at 60 product and 120 test line-equivalents, without a spike.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The proof operation, the proof artifact, the gate runner's progress events and the requirement
named above. Until this Change lands, a result and its record can hold what a gate printed.

Owner: the release lead. Next action: design the mask and the carriers it covers, once a gate
can name a variable. Read again: at the cut that follows the landing of
`gate-child-environment`.
