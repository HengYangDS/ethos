+++
title = "A first CI projection needs two commits in an order that neither refusal names"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Make two commits in this order: the runner declaration alone, then the pipeline's source together with its generated pipelines."
+++

A first CI projection is refused in one commit and needs two in this order, which neither refusal
names: the runner declaration alone, then the pipeline's source together with its generated
pipelines.
