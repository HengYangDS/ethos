## Why

Ownerless closeout currently validates every row in the shared lease table
before it filters for one target branch. Historical legacy rows belonging to
other branches therefore make an otherwise exact target observation
unverifiable and prevent the native closeout fence from reaching the target's
real admission boundary.

The failure is a read-boundary defect, not evidence that unrelated historical
rows may be rewritten or discarded. Closeout must keep the schema and the
exact target row fail-closed while excluding unrelated rows at the SQL query
boundary.

## What Changes

- Select lease rows with a bound exact `subject = ?` predicate before strict
  lease validation.
- Reuse that exact-subject validator for read-only ownerless state observation
  and transactional closeout-fence acquisition.
- Preserve strict rejection of a malformed exact-target row, current valid
  lease or Claim coordination, invalid schema, ambiguous expiry, and fence
  damage.
- Add focused regression coverage for unrelated legacy rows, malformed exact
  rows, fence acquisition, and native admission plus fenced re-observation.
- Add two successor target Claims and effect-admissible Chronicles. After this
  carrier is accepted, each authorizes one fresh direct-retire decision for its
  exact branch and HEAD; prior Chronicle-invalid, state-unverifiable, and stale
  decisions remain immutable and non-reusable.
- Leave all lease rows, maintenance policy, schema, lifecycle commands,
  foreign Work Lanes, and package records unchanged.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=ownerless-target-scoped-lease-observation;
  reuse=extend; change=modify; facet:lifecycle=resolution,retirement,observation;
  facet:surface=state-store,native-admission,tests,evidence;
  facet:authority=exact-target,lease-schema,accepted-head. Ownerless closeout
  validates only the exact target lease row after validating the canonical
  lease schema.

## Impact

- One existing private state-store module, three existing focused test owners,
  one OpenSpec carrier, one cohort Claim and Chronicle, two target Claims and
  Chronicles, supersession state on two prior target Claims, and parity
  evidence.
- No public API, schema, dependency, package root, `__init__.py`, maintenance
  behavior, lease mutation, raw SQLite edit, remote, or hosted-provider change.

## Out of Scope

- Migrating or deleting legacy lease rows; weakening exact-target validation;
  reusing stale lane-resolution decisions; changing either target disposition
  before a fresh accepted-ancestor no-effect result; clearing preservation
  packages; broad filesystem cleanup; GitLab or other network work.
