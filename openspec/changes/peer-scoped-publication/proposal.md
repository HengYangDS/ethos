## Why

A repository can declare GitLab and GitHub as independent publication peers,
yet the current `ethos publish` request observes both before it can create an
effect. If one peer is unavailable, the other cannot receive an exact,
receipt-bound update. That makes an advertised alternative distribution path
unusable at the moment it is needed. Removing a peer from the tracked release
declaration or pushing outside ETHOS would weaken the intended boundary.

## What Changes

- Add an invocation-local, repeatable `--peer <declared-id>` selector to exact
  `ethos publish --ref` requests. Without it, the command retains the current
  all-peer behavior. There is no automatic failover.
- Compile only the selected declared peers into the immutable request and
  recheck each selected ID-to-remote binding, source, proof, ref policy and
  exact-CAS coordinates before effects and during replay.
- Report declared, selected and unselected peers distinctly. A successful
  selected-peer effect does not claim publication to an unselected peer.
- Reject unknown or duplicate peer IDs and a new selector supplied alongside
  an existing receipt. Cover a healthy GitHub peer with an unavailable GitLab
  peer, plus forged or drifted bindings, through public native tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: permit an explicit subset of declared publication
  peers without weakening source, proof, topology or per-peer transaction
  admission.

## Impact

The existing `publish` CLI, application projection, request compiler, effect
admission, result projection, tests and command reference. No new state store,
remote credential path, Git effect primitive or repository-specific fallback
script is introduced.
