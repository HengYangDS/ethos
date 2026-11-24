+++
title = "A host proof waits in the host queue although a readiness gate already failed"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Run `ethos prove --readiness --execute` first."
+++

A host proof asks for its host ticket without testing the results of its readiness gates, so a proof
that a readiness gate fails still waits in the host's queue. Run `ethos prove --readiness --execute`
first.
