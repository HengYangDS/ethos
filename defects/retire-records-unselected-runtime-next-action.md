+++
title = "Record retirement from an unselected build refuses with an empty next action"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Run the preview and the apply with the selected runtime."
+++

The preview and the apply of `ethos hook retire-records` from a build that the repository has not
selected refuse with `record_retirement_runtime_unselected` and an empty next action. Run them with
the selected runtime.
