## Why

ETHOS can observe a clean linked Work Lane whose exact HEAD is already equal to
or an ancestor of accepted truth, yet its public `lane retire landed` path still
requires an executable proof Attestation and a valid historical Lease. That
turns deletion-only residue cleanup into a lifecycle dead end and has repeatedly
forced adopters to bypass the reference-transaction hook.

## What Changes

- Make `lane retire landed` compile retirement as a pure Git repository effect
  with no Commitment or proof-Attestation dependency.
- Admit clean linked lanes whose exact HEAD is accepted or an accepted ancestor
  when the Lease is either valid for the invoking holder, expired, or absent.
- Remove an exact valid or expired Lease row in the same bounded transaction;
  require an absent Lease to remain absent.
- Continue to block dirty lanes, non-ancestor heads, unknown Lease state,
  foreign valid holders, stale refs/worktrees, and changed accepted coordinates.
- Reuse the existing command, exact CAS executor, worktree effect, Lease store,
  and effect Attestation. Add no command, carrier, registry, compatibility path,
  or historical proof reconstruction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Define positive deletion-only retirement for clean
  linked Work Lanes already absorbed by accepted truth.
- `command-plane`: Bind Work Lane write admission to the four-field Lease and
  keep the expected Git HEAD in fresh mutation facts rather than Lease state.

## Impact

- `src/ethos/adapters/mutation/lane_retirement/linked.py`
- `src/ethos/adapters/mutation/lane_retirement/effects.py`
- `src/ethos/adapters/mutation/lane_retirement/linked_effect.py`
- focused retirement tests
- `openspec/specs/command-plane/spec.md`
- `openspec/specs/repository-governance/spec.md`

Out of scope are dirty or diverged-lane adjudication, detached cleanup,
proposal-ref retirement, remote publication, and broader lifecycle redesign.
