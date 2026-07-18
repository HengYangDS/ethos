# Design

`tools/ci/scripts/run-local-ci.sh` already guards HEAD stability around the local
CI run. The script now writes a small JSON manifest after successful owner-script
execution. The manifest records the stable head, command, generation time, and
explicit false claims for hosted CI and remote publication.

`ethos publish --json` reads that manifest through the land-support domain and
projects `evidence_status` into both the top-level local fallback package and the
submit-package fallback view. The status is deliberately small: `missing`,
`invalid`, `stale`, `current`, or `not_checked`, plus current/evidence HEADs and
the next local evidence action.

The design does not make generated fallback evidence repository truth. The
manifest is local fallback evidence only; tracked source, tests, schema, OpenSpec,
claim, and proof remain the durable product truth.
