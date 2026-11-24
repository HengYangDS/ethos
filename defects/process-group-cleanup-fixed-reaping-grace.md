+++
title = "A command's cleanup fails when its exited process group is not reaped within half a second"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

When a command's process scope closes, the product signals the command's process group. On macOS
that signal is refused with `PermissionError` while the group's leader is exiting, or while its
exited members await their reaper. The cleanup waits a fixed grace for the group to be reaped,
half a second unless the caller's own cleanup deadline is later, and then raises the error. On a
loaded host, or under a launch at low priority, a command that itself finished can therefore fail
in cleanup. Measured 2026-11-20: a landing started at nice 15 failed this way in two of two runs.
Read again in the source on 2026-11-25; not measured again.
