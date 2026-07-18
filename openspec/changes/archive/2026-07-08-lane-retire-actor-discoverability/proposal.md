# Lane Retire Actor Discoverability

## Problem

`ethos lane retire-landed` correctly refused to retire a leased Work Lane when
`ETHOS_ACTOR` was unset or did not match the lane lease owner, but the blocked
payload did not reveal the actor source or required actor. Humans and agents had
to infer the missing binding from implementation details.

## Change

Keep the existing owner-only retirement rule and `ETHOS_ACTOR` binding. When
landed-lane retirement is blocked by actor authority, include the actor source,
current actor binding state, required lease owner, and a bounded next action in
the command payload.
