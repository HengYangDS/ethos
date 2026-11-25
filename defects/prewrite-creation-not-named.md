+++
title = "`lane prewrite` does not say that an admitted path is a file about to be created"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Check that each requested path exists before asking, and pass one `--paths` for each path."
+++

A path that names no file is admitted as a creation, and the result does not say so. A caller who
mistyped a path, or joined two paths into one argument, receives a passing answer for a file that
does not exist and cannot see from the answer that the files it meant were never asked. Found
2026-11-21 in a governed repository.
