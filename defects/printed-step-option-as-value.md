+++
title = "A printed step with an option where a value belongs reads as live and is refused when run"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

A printed step whose argv has an option where a value belongs, such as `status --root --json`, is
read as a live step of that operation, and the CLI refuses the same argv when it is run, with
`command_usage_invalid`.
