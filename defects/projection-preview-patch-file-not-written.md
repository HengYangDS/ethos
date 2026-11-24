+++
title = "A projection preview's next action asks for a patch file that no command writes"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "Write the `patch` entry of the preview's JSON result to a file, byte for byte, and pass that file to `--patch`."
+++

A preview of `ethos lane project` that finds drift names as its next action
`ethos lane project --apply --authorize --expect-head <head> --patch <preview.patch> --json`. The
apply admits only the previewed patch, read from the file that `--patch` names, and no option of
the command writes that file. The JSON result carries the patch as the entry `patch` of its `data`,
so a caller copies it into a file byte for byte. A result over the payload bound of 16 KiB does not
print that entry: a string larger than 1,024 bytes moves to the full result that `bound` names,
and the printed result lists it under `bound.moved`. Reported 2026-11-19 under 0.2.0-beta.10; read
in the source on 2026-11-25, not run.
