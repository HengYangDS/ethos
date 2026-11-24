+++
title = "A gate's child process receives the launch's tokens and SSH agent socket"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Launch a proof from an environment that holds no credential which a gate should not see."
+++

A gate's child process receives the environment of the process that launched the check, the launch's
credentials among them: its tokens and the socket of its SSH agent. Only named tool variables are
removed. Launch a proof from an environment that holds no credential which a gate should not see.
