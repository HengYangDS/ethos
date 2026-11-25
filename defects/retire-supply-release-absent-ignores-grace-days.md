+++
title = "The release of absent consumers accepts `--grace-days` and ignores it"
state = "open"
since = "v0.2.0-beta.12"
fixed_in = ""
workaround = "none"
+++

`ethos hook retire-supply --release-absent --grace-days N` accepts the option and ignores it: the
absent-consumer path passes no grace period, so the request reads as though N were 7 for every
preview and apply, and a plan digest taken with one N is accepted under another. Read in the code:
the path that releases absent consumers calls its reader without a grace period, and that reader
takes none. No command refuses the pair today; either the two paths share
one meaning of N or the pair is refused by name.
