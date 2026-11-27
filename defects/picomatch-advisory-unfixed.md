+++
title = "Three shipped picomatch copies carry an advisory that no picomatch release fixes"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

GHSA-fc5q-39xc-vjpf (CVE-2026-112366) named every picomatch release through 4.0.7, and no release
fixed it. The product ships three copies: 4.0.7, the 4.0.5 that npm 12.2.3 bundles, and the 2.3.2
that markdownlint-cli2 0.24.1 reaches through micromatch 4.0.8.

The advisory was withdrawn on 2026-11-18, and the native npm audit no longer reports any of the
three copies. This repository's policy no longer accepts the two copies that it accepted; no
picomatch copy changed.
