# Proposal

## Why

The owner asked on 2026-11-14, as relayed by the adoption session, whether automatic build and
release follow one paradigm in every governed repository, and directed that a repeated wheel or an
accidental difference is abstracted and held by the common base.

That session's census of 14 governed repositories:

- 6 use the common pipeline model that `ethos lane project` generates from a declaration of four
  or five lines; three of the declarations are equal byte for byte.
- 1 declares the policy and generates with its own tool, and 2 have their own generators.
- 2 keep a pipeline written by hand, of 1,188 and 141 lines, and 2 have none.
- Only ETHOS has a release job in a workflow. Every other repository releases by hand or by a
  session's script.

The copies run before 0.2.0-beta.11 added one fact: a generated pipeline that no longer equals
its declaration is reported only by `ethos lane project --check`. No proof reads it, and 6
repositories held 12 such files.

## What Changes

Candidates, by the plan's existing owners:

- The release leg as a common model, which the common-base plan commits to 0.3.0 as its release
  operation.
- A migration path for the repositories with their own generators, through the CI template of the
  same plan.
- A proof, or the status reader, reports a generated pipeline that differs from its declaration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The pipeline model, the projection and the release operation. It adds reports first; a refusal
for a governed repository follows the rule row's order.

Owner: the release lead. Next action: place each candidate in the 0.3.0 order when that order is
written. Read again: after 0.2.0.
