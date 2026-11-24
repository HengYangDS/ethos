+++
title = "A full proof refused at host admission does not report the readiness gates that ran"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

A full proof whose host admission is refused does not yet report the readiness gates that ran before
the refusal. A host proof does, and it names the gates that did not run in `data.not_run`.
