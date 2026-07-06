# Protected OpenSpec Residue Gate

## Problem

Active OpenSpec carriers can be absent from the current checkout while still
remaining in a governed protected branch tree such as the configured release
root. If ETHOS only inspects the current worktree, that carrier residue stays
hidden until a later release or branch movement reintroduces it.

## Change

Surface active OpenSpec carriers found in configured release, accepted, and
candidate branch Git trees. The current protected checkout remains blocking when
it contains an active carrier. Non-current protected branch residue is advisory
visibility: it is a repository signal to repair the stale protected ref, but it
must not make the current accepted-root report claim failure for a different
truth horizon.
