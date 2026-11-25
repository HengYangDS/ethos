+++
title = "Reclamation of a generation differs by Python version under an unsearchable directory"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = "v0.2.0-beta.12"
workaround = "none"
+++

The reclamation of a generation gives the interpreter's answer for a listed path below a directory
that cannot be searched: it defers under Python 3.12 and 3.13 and reads the path as absent under
3.14.
