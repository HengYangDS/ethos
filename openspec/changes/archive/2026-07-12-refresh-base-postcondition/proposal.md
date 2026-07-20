## Why

`ethos lane refresh-base` currently treats a zero exit code from `git rebase`
as sufficient evidence that a stale Work Lane was refreshed. A runner, hook, or
host-signing failure can leave the ref unchanged while the command still emits
`state=base_refreshed`. That makes a control-plane success claim diverge from
the Git fact on which downstream proof and landing depend.

## What Changes

- Require every successful `refresh-base` path to prove that the captured
  candidate HEAD is an ancestor of the refreshed Work Lane HEAD.
- Block with `refresh_base_postcondition_failed` when Git reports success but
  that ancestry fact is absent.
- Apply the same check after automatic parity-projection recovery.
- Add a focused regression for a zero-code, no-op rebase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=work-lane-refresh-postcondition;
  reuse=extend; change=modify; facet:lifecycle=refresh;
  facet:surface=policy,tests,openspec; facet:authority=git,source,test.

## Out Of Scope

- Replacing Git rebase or adding an alternate mutation path.
- Treating host signing state as repository truth.
- Relaxing signature, lease, candidate-freshness, proof, or landing gates.

## Impact

The change is limited to the existing Work Lane refresh command and its
regression coverage. It adds no dependency and turns an unverified success into
an explicit, actionable block.
