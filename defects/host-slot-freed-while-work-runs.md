+++
title = "A host ticket's slot is freed while its work still runs when the holder is killed"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = "v0.2.0-beta.12"
workaround = "End a ticket's holder with an interrupt or a terminate signal, never with a hang-up or a kill; after a hang-up or a kill, end its child processes before another ticket is queued."
+++

`ethos host run` holds its place in the host queue by a file lock that the holder process
alone keeps open; the admitted command runs as its child and does not inherit that lock. A
holder that ends by an interrupt or a terminate signal removes its ticket and its child ends
with it. A holder that is killed, or that receives a hang-up, loses the lock at once while its
child runs on: the queue then reads no holder, admits the next ticket, and two heavy commands
run on a host whose declaration admits one. The first ticket's two files stay until the next
caller removes them.

Measured 2026-11-22 in a temporary fixture: after a hang-up and after a
kill the holder's child still ran, `ethos host status` listed no ticket, and a second
`ethos host run --wait 0` was admitted and removed the first ticket's files while the first
child was still running. A desktop application that quits sends a hang-up to the processes it
started.
