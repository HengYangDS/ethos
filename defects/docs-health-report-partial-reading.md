+++
title = "The documentation health report passes an oversized Change artifact that the gate refuses"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Rely on the documentation registry gate, not on the health report."
+++

The documentation health report measures the documents it is handed. Asked without the tracked
documents it reads the documentation root alone, so a Change artifact over the document ceiling
passes there and is refused by the documentation registry gate, which, asked at the repository's top
level, reads every tracked Markdown file. Rely on the gate.
