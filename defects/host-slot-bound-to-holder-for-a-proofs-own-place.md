+++
title = "For the place a proof takes for itself, a host slot stays bound to its holder"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "End a ticket's holder with an interrupt or a terminate signal, never with a hang-up or a kill; after a hang-up or a kill, end its child processes before another ticket is queued."
+++

The repair that lets an admitted command inherit its ticket's lock covers `ethos host run` on macOS
and Linux. For the place that a full proof or a host proof takes for itself, the slot is still a
lock that the holder process alone keeps: a holder that is killed frees the slot, whether or not
the processes it started have ended. Releases through 0.2.0-beta.12 had the same for every
ticket on Windows.
