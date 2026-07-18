# Design

This change does not add a new identity store, handoff channel, or authorization
path. It only makes existing Work Lane lease facts visible at the point of
refusal.

The retire payload remains a repository command result. The lease owner remains
local state under `.ethos/state`; `ETHOS_ACTOR` remains the explicit actor
binding. The command emits enough information to correct the binding or seek
handoff without granting write, land, or retire authority to observers.
