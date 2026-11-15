# Proposal

## Why

The release-candidate plan designs one reader of a commit's hosted runs. Two facts of 2026-11-15
belong to its acceptance:

- Five sessions run only on the forges: `external_links`, `host_conformance`,
  `hosted_verification`, `release_binary_scan` and `release_journey`. No gate of either registry
  runs them.
- A head passed its full proof of 34 gates, landed, and failed `host_conformance` on both forges
  within seconds, because a list of test names had no reader on the workstation. A later head
  failed one test on the forge first, for a link in a document that an installation carries.
- A landing does not ask whether its head has a hosted run. The release lane now refuses by its
  own script.

## What Changes

- The reader of hosted runs for one exact commit on each CI peer, as the release-candidate plan
  sizes it, with one reader and two keys.
- A named gap for a CI peer that holds no run of the observed head.
- The landing's preview states, as an observation, whether the proposal head has a hosted run on
  each CI peer and how it concluded. A job that the pipeline lets fail is not a failed run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

A new reader and its command; the landing's preview. No refusal is added in this release line: the
preview observes.

Owner: the release lead. Next action: confirm the plan's design against these facts and measure
the patch. Read again: at the cut of 0.2.0-beta.12.
