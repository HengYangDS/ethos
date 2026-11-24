+++
title = "A partial lane retirement cannot be resumed after the next landing, nor taken back"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Resume a partial retirement with `ethos lane retire recover` before another change lands."
+++

A lane retirement that stops after some of its effects keeps a receipt, and
`ethos lane retire recover` takes the remaining effects at the coordinates that the receipt binds.
Once the accepted branch has advanced while a worktree removal or a ref deletion remains, the
recover is refused with `retirement_accepted_coordinate_drift`. The next action is then derived
from current facts and, where no retirement route fits them, is a bare `ethos lane status` read.
The recover has no compensating form either: it reports the completed and the remaining effects
and takes the remaining ones, and no mode takes a completed effect back. Measured 2026-11-20 in a
fixture; read again in the source on 2026-11-25, not run. Whether any command ends the record of a
retirement that can no longer be resumed was not established.
