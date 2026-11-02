# Proposal

## Why

ETHOS publishes through `run_network_git`, which drops every `GIT_CONFIG_*` overlay so that no
configuration can redirect the exact push. Git's sparse pack walk (`pack.useSparse`, on by default)
"walks trees that appear in paths that introduce new objects" and can add extra objects "if the
included commits contain certain types of direct renames" (`git help config`). On 11-02 an
adopter's lane that moved whole directories pushed a 29 MiB pack, which GitLab refused at its
20 MiB limit; the same push without the sparse walk was 1 MiB. The adopter could only set the
option in its repository's local configuration for one push and unset it again.

## What Changes

- ETHOS's publication push runs `git -c pack.useSparse=false push …`, so a rename batch sends only
  the objects the receiving peer lacks. No caller can set other options; the exact-lease refspecs
  and the native pre-push admission are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The push stays the same effect with a smaller pack, so `skip_specs: true` applies.

## Impact

`src/ethos/adapters/mutation/publication/execution.py` and its tests. A push of a small change in a
very large repository may take longer to compute its pack.
