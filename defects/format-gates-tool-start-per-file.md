+++
title = "The format gates start a tool once per file where one start for all files suffices"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = "v0.2.0-beta.12"
workaround = "none"
+++

The format gates start a tool once for each file where one start for all files suffices: the
Markdown lint gate renders each Markdown file alone, and a repository with a Prettier ignore file of
its own sends every Prettier file down that path. Measured: on this repository the Markdown lint
gate took 36.1 s where 4.7 s suffice; on one governed repository with its own ignore file three
format gates took 140.5 s where 8.7 s suffice. The verdicts are right.
