# Retire Owner Boundary

## Problem

`ethos lane retire-landed` could plan retirement for a landed foreign Work Lane
from the accepted root because merge status alone was treated as enough. That made
visibility look too close to authority: a lane could be observable and landed, yet
still belong to another agent's work lane.

## Change

Require landed-lane retirement to bind the current actor to the lane lease owner.
The existing lease remains the authority signal; no new truth store or command
surface is introduced. Missing leases and mismatched actors block with
`foreign_work_lane_retire_authority_required`.
