+++
title = "One unreadable lock file in the host queue refuses every admission"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Restore the file's permissions or remove it from the host queue directory."
+++

A lock file in the host queue that the reading user cannot open for writing, through its mode or
an immutable flag, makes every read of the queue answer `host_admission_unavailable`. No run is
admitted until the file is repaired or removed; no later read removes it.
