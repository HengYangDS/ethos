+++
title = "Three shipped picomatch copies carry an advisory that no picomatch release fixes"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

GHSA-fc5q-39xc-vjpf (CVE-2026-112366) names every picomatch release through 4.0.7, and no release
fixes it. The product ships three copies. ETHOS reports one and does not block: 4.0.7, the
registry's latest. The 4.0.5 that npm 12.2.3 bundles is accepted with the two findings of the record
`npm-bundled-glob-minimatch-advisories`. The third, 2.3.2, is what markdownlint-cli2 0.24.1 reaches
through micromatch 4.0.8; each of those is its registry's latest, and micromatch takes the 2.x line
alone, so no upgrade removes it. The audit blocks it as a finding behind the latest release, and
this repository's policy accepts it until 2026-12-02 for its own lock; the acceptance covers no
other repository's lock.

The Markdown lint gate runs the matcher as a local command over the file names and the lint
configuration of the repository that it judges. A pattern there can make that gate slow; the matcher
serves no request.
