+++
title = "A repository formed with the `python-library` starter fails its own proof preview"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "After forming the repository, in its first lane: lock the project (`uv lock`) and make the project's version follow the `VERSION` file, as the two gaps name; or form with the `foundation` starter and add the Python project afterwards."
+++

`ethos adopt --create --starter python-library` forms a repository whose `ethos status` answers
`pass`, `ready`. Its first `ethos prove` answers `block` with two gaps of the repository paradigm:
`repository_paradigm_module_lock:pyproject.toml` (the starter writes a `pyproject.toml` and no
`uv.lock`) and `repository_paradigm_version_source:pyproject.toml:project.version` (the starter
writes `version = "0.1.0"` beside a `VERSION` file that holds `0.1.0-alpha.0`). The `foundation`
starter forms a repository whose proof preview passes. So a new Python project cannot prove its
first commit as formed, and `status` does not say so.
