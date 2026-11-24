+++
title = "A newer runtime's console answers with the older build that the lane selected"
state = "open"
since = "v0.2.0-beta.7"
fixed_in = ""
workaround = "To preview with the newer build, run its interpreter directly: `<runtime>/python/bin/python -B -I -m ethos.cli lane repair-paradigm --root <lane> --json`, or select it first. A result names the build that answered in `summary.runtime`."
+++

In a lane whose selected runtime is an older release, a newer runtime's `ethos` console re-executes
in the selected runtime, so a preview such as `ethos lane repair-paradigm` answers with the older
build's result. To preview with the newer build, run its interpreter directly:
`<runtime>/python/bin/python -B -I -m ethos.cli lane repair-paradigm --root <lane> --json`, or
select it first. A result names the build that answered in `summary.runtime`.

The same holds for every command but `hook install` and `release accept`: until the newer build
has run `ethos hook install` in the repository, `ethos status` is answered by the older build and
says nothing of the newer console (measured 2026-11-23). Called by the newer build's interpreter,
`status` answers `write_admission_not_armed:runtime_build_stale`.
