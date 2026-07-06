# Advisory Next Action Readmodel

## Problem

ETHOS now exposes non-blocking advisory governance signals, but a visible small
signal still decays into noise if the first-glance reader view does not show the
bounded next action for inspecting or repairing it.

## Change

Add bounded advisory `next_actions` to report and orient reader views. The
signals remain non-blocking and do not authorize protected-root mutation.
