+++
title = "A refused `--runtime` value at hook installation does not say which condition failed"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

`ethos hook install --runtime` with a value that is no absolute, unlinked runtime root answers
`hook_install_failed:hook_runtime_current_target_invalid`; its next action is
`ethos status --root <root> --json`, and nothing says which condition failed.
