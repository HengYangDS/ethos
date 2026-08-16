# Design

## Context

`resolve_git_effect_repository` already admits one bounded v1-to-v2 repository
transition when a plan declares `repository_commitment_bootstrap` and binds the
exact v1 repository ID and bytes. Commitment rebind uses this contract; landing
did not project it when its target candidate still carried terminal v1.

## Decision

Candidate plan compilation inspects only the exact expected candidate head. If
that head contains a valid terminal-v1 repository carrier, the plan includes the
existing bootstrap marker and exact prestate coordinates. Otherwise it emits the
unchanged normal candidate policy. Shared effect admission remains the sole
identity validator.
