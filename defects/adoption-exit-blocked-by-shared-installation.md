+++
title = "An adoption exit is blocked while any process on the host runs from the shared installation"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Preview and apply the exit at a moment when nothing on the host holds or waits for a host ticket."
+++

`ethos adopt --exit` refuses with `adoption_exit_runtime_in_use` when a process on the host
references a path under the runtime that the repository's selector names. Where that runtime is
the host's shared installation, every `ethos host run` of every other repository is such a
process: a waiting ticket runs for as long as it waits. On a host with a standing queue the exit
can then never pass, although it removes nothing of the shared installation.

Reported 2026-11-22 from a read-only preview on a governed repository (at least five such
processes served other repositories, one under a six-hour bound). Read in the source
(`adapters/repo/hook/exit_plan.py`, `_blockers`): the test is whether any process reference lies
under the installed runtime's path, with no regard to which repository the process serves. The
report was not reproduced on that repository.
