## Context

`EthosResult` already owns the public typed boundary and invokes the shared
false-pass check. The missing public cases are reasonless `unknown` and `block`.
Internal decisions may carry their rationale in their existing `why` field and
are not changed here. Separately, `lane status` calls
`report_verdict` on `workspace_status`, although that mapping carries facts and
gaps rather than an owned verdict; the absent verdict is therefore interpreted
as `unknown`.

## Decision

Strengthen the existing public result owner:

- `unknown` requires at least one named missing fact or evidence gap;
- `block` requires at least one named gap or adverse diagnostic;
- `pass` remains incompatible with gaps or adverse diagnostics.

`lane status` shall reduce the explicit workspace validation verdict and the
complete gathered gap set. It shall not treat the facts-only workspace mapping
as another decision owner.

## Deletion

Delete the `report_verdict(report)` input from `lane status` and migrate every
test fixture in this boundary that encoded reasonless non-pass values. Do not
add a fallback gap, inferred error string, or parallel verdict helper.
