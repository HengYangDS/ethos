+++
title = "A finished host run reports no command status when its queue place cannot be given up"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

When a run under `ethos host run` has ended and its place in the queue cannot be given up, the
result is `host_admission_unavailable` without the command's own status; a host proof in that state
reports no check.
