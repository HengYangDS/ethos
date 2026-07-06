# Land Role Boundary

## Problem

`ethos land --json` is the work-lane-to-candidate readiness surface. On protected
roots, a clean repository could report `ready_to_land`, which blurred normal land
with accepted-root closeout.

## Change

Make dry-run land admission role-aware: protected roots are blocked for normal
land and point users to `ethos land --closeout --json`. Keep authorization,
expect-head, and executed-proof requirements apply-only.
