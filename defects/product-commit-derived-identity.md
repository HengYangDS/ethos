+++
title = "A commit or tag that the product makes can carry an address derived from the host"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Set `user.name` and `user.email` in the repository's own configuration; the signer authorization reads its principal from the same `user.email`."
+++

A commit or a tag that the product itself makes can carry an address that Git derived from the
host's user name and host name. The product's Git reads no system and no global configuration, so an
identity that only the global configuration holds is not read. It happens where the repository's own
configuration names no `user.email`, the product's process holds no `GIT_AUTHOR_*`,
`GIT_COMMITTER_*` or `EMAIL` variable, and, for a commit, the commit policy declares no author or
committer.

Measured: a fixture commit through the product's own commit maker carries the derived address, where
plain Git with the identity in the global configuration carries the configured one. Read in the code
and not run: the commit of `ethos lane archive-change` and the product's merge commit pass no
identity of their own, and a release tag takes its tagger the same way. One governed repository
reported ten such commits and one tag in its public history. Set `user.name` and
`user.email` in the repository's own configuration; the signer authorization reads its principal
from the same `user.email`.
