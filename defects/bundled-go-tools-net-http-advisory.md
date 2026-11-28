+++
title = "Bundled CUE, Vale and shfmt are built with Go versions that a net/http advisory names"
state = "open"
since = "v0.2.0-beta.8"
fixed_in = ""
workaround = "none"
+++

Go's GO-2026-6859 (CVE-2026-97054) lets an HTTP/1 server in `net/http` crash; Go 1.26.11 and 1.27.4
fix it. The bundled `cue` 0.17.1, `vale` 3.29.0 and `shfmt` are built with Go 1.26.5, 1.27.3 and
1.27.1 and contain the affected code. ETHOS runs them only as local commands over repository files
and starts no HTTP server through them; a later supply move takes releases built with a fixed Go.
