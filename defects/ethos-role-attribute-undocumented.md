+++
title = "No documentation page states the Git attribute that sets a carrier's role"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Mark such paths with `ethos-role` in `.gitattributes`, as this repository's own file does for its tools."
+++

The Git attribute `ethos-role`, which the product reads as a carrier's role, is stated in no page
under `docs/`; one repository met 323 files that asked for behavior evidence before it found the
attribute in the source. Mark such paths in `.gitattributes`, as this repository's own file does for
its tools.
