# Design

## Context

See the [proposal](proposal.md). The installed runtime compiles the gate policy of a candidate head
with its own declaration contract, and a landing requires that policy to equal the candidate's own.
A runtime without the provider catalog refuses a registry that names a catalog ID, so the registries
switch only after the installed runtime carries the catalog.

## Goals / Non-Goals

Goals:

- Every provider gate of the shipped registries names a catalog ID.

Non-Goals:

- Removing a legacy name from the catalog, which is the later, Breaking contract step.
- Any adopter's registry.

## Decisions

1. Both registries switch in one Change. A repository's declaration of a shared gate composes with
   the packaged one under either spelling, so the packaged registry needs no order against any
   adopter's registry.
2. The hosted proof wrapper names the Python test gate's provider by its ID in the same Change: it
   finds the gate's report by the declared name, which this Change alters.
3. The table-driven test tightens from "the catalog resolves every shipped reference" to "every
   shipped reference is a catalog ID", so a legacy name cannot return to a shipped registry.

## Risks / Trade-offs

- Control-replacement admission compares gates by their declared fields, so it lists each of the 19
  provider gates of the full proof as a changed obligation. The gates' providers are unchanged; an
  independent verification that the profile requires must cover that floor.
- A rollback to a runtime without the catalog refuses these registries. Restore the registries of
  the earlier head before such a rollback.
