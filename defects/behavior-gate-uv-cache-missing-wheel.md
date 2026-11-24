+++
title = "The behavior gate fails inside a proof when uv's cache lacks a locked wheel"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Fill the cache first with one online `uv sync --locked` by the uv that the repository pins."
+++

The behavior gate builds its environment from uv's cache alone. On a host whose cache lacks a locked
wheel, for example after a cache cleaner, the gate ends inside the proof with
`test_environment_sync_failed`. Fill the cache first with one online `uv sync --locked` by the uv
that the repository pins.
