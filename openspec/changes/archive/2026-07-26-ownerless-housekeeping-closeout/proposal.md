## Why

The completed native closeout still leaves three clean, missing-lease Work
Lanes that are diverged from accepted truth. Two are historical predecessors
whose exact commits remain reachable from valid-owner successor lanes; the
third carries one unique, unaccepted release-date edit. Treating all three as
generic garbage would either violate active ownership or discard recoverable
intent.

## What Changes

- Add one narrow accepted authority carrier with a separate exact Chronicle
  and Claim for each missing-lease branch and HEAD.
- Select direct native `lane_resolution/retire` for the two source-admission
  predecessors only while fresh observation proves their exact commits remain
  reachable from the valid-owner successor lineage.
- Select native `lane_resolution/preserve-retire` for the unique release lane;
  retain and verify its recovery package without claiming that its release date
  was accepted or remotely published.
- Keep the seven valid-owner lanes observe-only. Dirty or leased work is not
  normalized, reset, retired, or absorbed by this Change.
- Repair the accepted native-lane-resolution Claim and Chronicle so they record
  the already completed exact-HEAD proof, candidate/accepted closeout, local
  publish readiness, and task-lane retirement without upgrading those local
  facts into hosted or remote evidence.
- Limit final filesystem cleanup to reviewed unregistered cache-only directories
  and ignored WCP bytecode after all tracked and Work Lane transitions finish.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=ownerless-housekeeping-closeout;
  reuse=extend; change=modify; facet:lifecycle=resolution,retirement,housekeeping;
  facet:surface=openspec,claim,evidence,cli; facet:authority=git,lease,chronicle,
  accepted-head. Clean ownerless divergence must distinguish exact history
  retained by a valid-owner descendant from unique intent that requires a
  preservation package, while granting no authority over that descendant.

## Impact

- OpenSpec repository-governance delta, three target-bound Claims and
  Chronicles, and the final native-resolution Claim/Chronicle repair.
- Candidate-external lane-resolution decisions, completion receipts, and one
  retained recovery package for the release lane.
- No product source, package API, dependency, remote ref, hosted provider, or
  valid-owner Work Lane mutation.

## Out of Scope

- Handoff, land, retirement, cleanup, or semantic judgment for the seven lanes
  with valid leases.
- Remote probing, push, tag or release publication, hosted-CI claims, recovery
  package clearing, raw Git cleanup, SQLite edits, or session/IDE mutation.
