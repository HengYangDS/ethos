## Context

Official OpenSpec has distinct Change and specification namespaces. The current
adapter supplies only a name to `show`; a successful specification response has
no Change deltas and prevents the missing-Change archive fallback.

## Decisions

Use the official `show --type change` selector at the existing compilation
boundary. Preserve the existing attested archive resolver, exact source binding,
and expected Commitment digest checks. Do not infer type from spelling or add a
second parser. Invalid successful Change projections remain errors, not a reason
to silently substitute history.

Renaming the adopter's Change or capability would hide a valid namespace
collision. Falling back on every compilation error could conceal malformed
current intent. Neither alternative preserves the intended boundary.

## Verification And Migration

First reproduce the namespace conflict with the locked official CLI. A real
isolated repository exercises active selection, official archive, attested intent
recovery, candidate integration and accepted closeout. Synthetic proof fixtures
establish test prerequisites; they do not claim product acceptance.

Reject a missing Change without an applicable archive, wrong digest and malformed
successful projections. Review all official `show` consumers. After focused and
full verification, publish the accepted package; adopters use public runtime
installation and retry their exact closeout without changing source intent.

