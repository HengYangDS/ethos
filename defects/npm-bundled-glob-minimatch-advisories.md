+++
title = "The bundled npm ships glob and minimatch copies that two security advisories name"
state = "open"
since = "v0.2.0-beta.3"
fixed_in = ""
workaround = "none"
+++

npm 12.2.3, the registry's latest, still bundles glob 13.0.6 and minimatch 10.2.5, which
GHSA-3g3m-2fjr-6pw4 and GHSA-g3hv-75wg-m249 name. Their ranges end at glob 14.0.1 and below
minimatch 11.0.1, and the product's own copies, glob 14.0.6 and minimatch 11.0.9, are fixed
releases; but no npm release bundles a fixed version yet.

Without an acceptance the audit reports the bundled copies while npm 12.2.3 is the registry's
latest, and blocks on them once a newer npm exists, although that npm may bundle the same versions.
This repository's policy therefore accepts them until 2026-12-16 for its own lock; the acceptance
covers no other repository's lock.
