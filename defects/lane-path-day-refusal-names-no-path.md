+++
title = "A lane path with a day other than the UTC day is refused without the expected path"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "The expected path is the `path` field of the `--json` result; or omit `--path`."
+++

`ethos lane start` with a `--path` that carries another day than the lane's UTC day is refused with
`work_lane_path_not_canonical`, and neither the reason nor the next action names the expected path.
It is the `path` field of the `--json` result; or omit `--path`.
