+++
title = "A publication ends with an unknown outcome when the one read after its push fails once"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Run the probe and its apply again after a pause of some seconds."
+++

`ethos publish --apply` reads each peer once after its push. When that one read fails, the
publication ends as `outcome_unknown` with `publication_remote_observation_unavailable` and does not
go on to the next peer, although the push took effect. The next probe reads the peer once as well,
and a failure there ends as `preflight_unknown`. The read is a single `git ls-remote` with no second
attempt; it changes nothing on the peer, so a repeated read repeats no effect.

Reported from one governed repository on 2026-11-26, at a tag's publication to two peers: the first
peer's SSH endpoint closes a connection that is opened within seconds of another, so the read that
follows the push lost. The tag stood on the first peer alone until a third run, 35 seconds after the
second run's probe, published both. The result was truthful at each step; no run claimed a
publication that it had not read back.
