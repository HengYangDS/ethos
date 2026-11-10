"""The Git settings that keep every test repository inert and independent of the host."""

# No test repository depends on a host filesystem monitor, and none repacks or prunes itself in a
# detached process after a commit, so its objects stay exactly as the test wrote them.
GIT_ISOLATION = (("core.fsmonitor", "false"), ("maintenance.auto", "false"))
