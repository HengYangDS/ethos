+++
title = "An installation that only a vanished repository recorded stays in the shared store"
state = "closed"
since = "v0.2.0-beta.7"
fixed_in = ""
workaround = "none"
+++

An installation that only a moved, unmounted or deleted repository recorded stays in the shared
store, because no command releases an absent consumer yet; `hook install`'s cleanup report lists
such consumers under `absent`.
