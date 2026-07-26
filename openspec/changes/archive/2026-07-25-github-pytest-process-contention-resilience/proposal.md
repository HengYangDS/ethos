## Why

GitHub Actions run `30155639504` failed repository proof twice for accepted
commit `626ab408d`. The first attempt timed out two Git-backed lifecycle tests
at 300 seconds; the failed-job rerun reached 99% before failing two different
source-budget tests. This changing failure set is inconsistent with a single
deterministic product defect and points to process and Git contention under the
four-worker self-hosted macOS projection.

A complete two-worker diagnostic on current accepted commit `8555afde7`
executed all 3,557 tests. It passed the four tests implicated by both hosted
attempts and reported 3,556 passes; the only failure was the expected governance
check that this new Work Lane did not yet have a tracked Claim binding.

## What Changes

- Reduce only the GitHub macOS repository-proof projection from four pytest
  workers to two.
- Retain the finite 300-second signal timeout and owner-script validation.
- Keep the canonical GitHub template and generated workflow identical.
- Update the provider-projection architecture contract and current quality
  specification.
- Add the two missing list-boundary blank lines in the accepted snapshot replay
  implementation plan so the Markdown owner gate can reach repository proof;
  no prose content changes.
- Keep GitLab at one worker, the repository-wide pytest defaults unchanged,
  and the source-budget worker resource contract unchanged.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=github-pytest-process-contention-resilience; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=ci,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Changing GitLab's single-worker Docker projection or probing GitLab while the
  current workstation is outside the intranet.
- Changing the product source-budget worker's eight-second resource contract.
- Raising individual test timeouts, suppressing failures, or adding automatic
  retries.
- Changing runner hardware, runner labels, or foreign Work Lanes.

## Impact

The canonical GitHub Actions template, its generated workflow projection, one
architecture contract, the quality specification, two blank-line repairs in one
accepted implementation plan, bounded OpenSpec/Claim/Chronicle evidence, and
generic parity evidence. No dependency, product runtime, or GitLab change.
