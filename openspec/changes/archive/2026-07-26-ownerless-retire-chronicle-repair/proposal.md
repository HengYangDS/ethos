## Why

The first accepted budget-predecessor `lane_resolution/retire` decision was
recorded correctly, but effect admission stopped before ancestry evaluation
with `lane_resolution_ownerless_chronicle_invalid`. The accepted Chronicle
carried `event: lane_resolution/retire` in front matter but omitted the exact
standalone effect token required by the current native closeout contract.

## What Changes

- Preserve the original archived carrier and pending decision as immutable
  no-effect evidence; do not rewrite or clear local resolution records.
- Add a successor Claim and Chronicle cohort that binds decision
  `lane-decision:6e57ce11-5723-4171-85a8-596452f118fa`, its exact target, and
  the observed `lane_resolution_ownerless_chronicle_invalid` result.
- Add one new target-bound Chronicle and Claim for each of the two budget
  predecessors. Each Chronicle retains the accepted semantic judgment and
  includes the exact standalone `lane_resolution/retire` effect token.
- Supersede only the earlier cohort and two budget target Claims after the
  successor evidence exists. The completed release preservation Claim and
  package remain unchanged and retained.
- After this successor is archived, proved, landed, and accepted-closed, record
  new direct-retire decisions. Any accepted-ancestor no-effect result remains a
  separate input to the already required preserve-retire reconciliation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=ownerless-retire-chronicle-repair;
  reuse=extend; change=modify; facet:lifecycle=resolution,retirement,repair;
  facet:surface=openspec,claim,chronicle,evidence;
  facet:authority=accepted-head,chronicle,git,decision. Accepted direct-retire
  authority must be effect-admissible before a new irreversible decision is
  recorded.

## Impact

- One narrow OpenSpec successor, three new Claims, three new Chronicles, and
  supersession state on the prior cohort and two budget Claims.
- No product source, test, schema, dependency, package API, valid-owner Work
  Lane, protected ref, remote, hosted provider, recovery package, SQLite row,
  or session/IDE mutation in this Change.

## Out of Scope

- Bypassing native Chronicle or accepted-ancestor admission; reusing the
  invalid pending decision; applying preserve-retire before a later accepted
  reconciliation; clearing any retained package; touching valid-owner lanes;
  remote probing, push, tag/release publication, or hosted-CI claims.
