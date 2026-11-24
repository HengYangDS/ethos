+++
title = "During template drift in a Change artifact, a prewrite calls every other path uncovered"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Write only the paths that the answer authorizes, restore the artifact's headings, and ask again."
+++

While an artifact of a Change has template drift, a prewrite calls every path but that artifact's
own uncovered, `openspec_material_path_uncovered:<path>`, and points to `ethos status --json`. Write
only the paths that the answer authorizes, restore the artifact's headings, and ask again.
