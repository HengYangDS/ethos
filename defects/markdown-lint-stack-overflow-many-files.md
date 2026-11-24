+++
title = "The `markdown-lint` gate ends in a stack overflow when one proof lints well over a thousand files"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

In a repository with 1,339 Markdown files, the `markdown-lint` gate of a proof ran for 330 seconds
and failed: the bundled markdownlint (0.42.1, under markdownlint-cli2 0.24.1 and Node 26.13.1)
ended with `RangeError: Maximum call stack size exceeded`, and the gate answered
`quality_gate_failed:markdown-lint` with no finding about any file. The gate's own format and
list-spacing parts passed. Observed once with 0.2.0-beta.11 in a temporary repository on
2026-11-23; the number of files at which it starts, and the behaviour of a later build, were not
measured.
