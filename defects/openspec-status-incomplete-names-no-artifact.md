+++
title = "The refusal `openspec_status_incomplete` does not name the artifact the Change lacks"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Read the missing artifact from `openspec status --change <change> --json`."
+++

`openspec_status_incomplete:<change>` does not name the artifact that the Change lacks. Read it from
`openspec status --change <change> --json`.
