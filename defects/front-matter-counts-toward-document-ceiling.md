+++
title = "A document's front matter counts toward the document line ceiling"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "Keep the body shorter by the front matter's lines, or declare the repository's own ceiling."
+++

A document's front matter counts toward the document ceiling: its fields and its two `---` lines,
seven lines in this repository's `docs/README.md`. Keep the body shorter by that much, or declare
the repository's own ceiling.
