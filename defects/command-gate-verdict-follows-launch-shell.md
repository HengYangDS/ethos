+++
title = "A declared command gate's verdict can follow the shell that launched the proof"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "Launch a local proof from the shell as it is, or under `env -i` with `HOME`, a system `PATH` and `TMPDIR`, and do not remove Mise's activation variables alone."
+++

A gate that a repository declares as a command receives the environment of the shell that launched
the proof, so its verdict can follow that shell. Measured on one governed repository, under
0.2.0-beta.11 and under 0.2.0-beta.10 alike: from a shell whose Mise activation variables had been
removed while its `PATH` stayed activated, a test of such a gate read the npm that Node bundles and
not the declared one (jdx/mise#15771), and the proof failed; from a clean environment it passed.

Launch a local proof from the shell as it is, or under `env -i` with `HOME`, a system `PATH` and
`TMPDIR`, and do not remove Mise's activation variables alone.
