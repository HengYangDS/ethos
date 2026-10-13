## Context

`command_scope` and `_execute_command` read time only through the module's `monotonic`. Any real elapsed time therefore enters the test through process start-up, which the test does not own.

The archive effect already holds the official validation report when it compensates a rejected postimage, but it passes only the derived gaps to `lifecycle_report`.

## Decisions

1. Replace the test's wall-clock margins with the adapter's own clock. Advance the caller's scope by a known amount and assert the nested command's effective timeout equals the remaining budget. The child itself is real, so the scope still terminates a live process.
2. Project native issues with one pure helper beside the existing gap derivation. Only `ERROR` and `WARNING` issues of items the validator marked invalid are carried, with their native level, path and message. The required gaps and their consumers are untouched.
3. The archive CLI forwards those issues as result diagnostics, following the existing diagnostics forwarding in `lane lease`.
