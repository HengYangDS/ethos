+++
title = "A path that only the user's global excludes file ignores makes the accepted root dirty"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "Keep the path out of the accepted root, or ignore it in the repository itself: its `.gitignore`, or `.git/info/exclude` for one clone."
+++

The product runs Git without the user's global configuration, so a `core.excludesFile` that this
configuration names is not read. A directory that a tool on the user's machine creates in the
accepted root, and that only that file ignores, is untracked to the product: `ethos status` counts
it as a changed path, and `ethos lane start` is refused with
`lane_start_requires_clean_accepted_root`. The refusal does not say that the global excludes file
is not read. Reported 2026-11-19 under 0.2.0-beta.10; read in the source on 2026-11-25, not run.
