# Proposal

## Why

The full proof must not leave hosted CI as the first observer of a defect, yet no proof gate
validates commit ranges. Local landing does run `commit_range_admission_report`, but inside the hook
process, with the installed runtime: a self-landing validates its commits with the predecessor's
code. So a new or tightened commit check first runs in the hosted jobs, which install the head's
own source. On 11-08 `cb8e65879` turned both peers red on `record_marker_malformed` after a passing
proof and a passing land.

## What Changes

- The ETHOS repository's gate registry gains `commit-ranges`, a read-only proof gate whose provider
  validates, with the candidate's own source, the commits that the next accepted and release pushes
  to each declared peer will carry, with each target's branch-role policy and the configured commit
  trust anchor.
- A peer without a tracking tip for a branch is an advisory; when no declared peer has one, the gate
  refuses with `commit_ranges_unobserved` instead of passing with nothing checked.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the full proof validates the commit ranges that the next publication carries.

## Impact

- `system/repository-gates.toml`, a provider under `src/ethos/adapters/gates/`, and the gate and
  provider tests.
- Only the ETHOS repository: an adopter's hooks and pipelines run one pinned runtime, so its local
  and hosted validations already agree.
