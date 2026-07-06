# OpenSpec Lifecycle Protected Advisory

## Problem

The repository scorecard could surface active OpenSpec carriers that remained in
a non-current protected branch, but the OpenSpec-specific lifecycle reader still
reported only the current checkout lifecycle. That left the dedicated OpenSpec
surface less informative than the aggregate report.

## Change

Reuse the protected-branch active-carrier scan in the OpenSpec lifecycle adapter
and expose the result as advisory state. The current checkout remains clean when
its own OpenSpec lifecycle is clean; non-current protected branch residue is a
visible repair signal, not a blocker for the current accepted root.

## Capabilities

- `command-plane`: subject=openspec-lifecycle-protected-advisory; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,openspec; facet:authority=source,test,openspec,evidence

## Out Of Scope

- No direct mutation of `main` or other protected branches.
- No new OpenSpec command plane or parallel truth store.
- No promotion of advisory signals into required gaps.
