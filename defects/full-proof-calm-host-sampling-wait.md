+++
title = "A full proof waits 15 seconds before its test gates on a calm host with a load limit"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = "v0.2.0-beta.12"
workaround = "none"
+++

On a host that declares a load limit, a full proof waits one sampling interval, 15 seconds, before
its test and package gates even when the host is calm and both slots are free.
