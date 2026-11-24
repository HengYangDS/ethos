+++
title = "The next action of `work_lane_name_dated` drops the `--base` of the refused request"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Add `--base <commit>` to the printed command."
+++

The next action of `work_lane_name_dated` drops a `--base` that the refused request named, so the
printed command starts the lane from the candidate. Add `--base <commit>` to it.
