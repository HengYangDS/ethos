# Design

## Context

See [proposal.md](proposal.md).

- **The incident.** beta.2's release run 41976538980 failed both journey legs with
  `release_journey_download_failed:v0.2.0-beta.1:release not found`, after it had published every
  runtime and the release itself.
- **The owner's decision.** On 2026-11-05 the owner chose not to publish 0.2.0-beta.1, because the
  rerun of its release run refused npm 12.2.1 after npm 12.2.2 fixed six of its advisories. The tag
  `v0.2.0-beta.1` stays as history, and the changelog entry records that the version was tagged but
  never published.
- **The journey.** `qualify` names the predecessor with `previous_version`, a pure function over
  the changelog. Then `download_release` fetches that tag's assets with `gh release download`.

## Goals / Non-Goals

Goals:

- The journey upgrades from the latest earlier release that the forge published.
- The receipt states which versions were skipped and why.

Non-goals:

- Any change to which assets are downloaded or how they are verified.
- Treating the changelog note as authority. The forge decides whether a release exists.

## Decisions

- **The forge is the authority for publication.** `previous_version` keeps its changelog walk, and
  it now receives a predicate for "was this version published". `qualify` passes one that asks
  `gh release view <tag> --repo HengYangDS/ethos` through the journey's existing process helper.
  The walk stays a pure, testable function.
- **Skips are evidence.** `previous_version` returns the chosen version together with the versions
  it skipped. The receipt records them under `skipped_unpublished`.
- **Same refusal.** A prerelease with no published earlier entry still refuses with
  `release_journey_previous_missing:<version>`.
- **No other consumer.** A search of `tools/` and `src/ethos` found no other code that treats the
  next changelog entry as the previous release. `release_assets.py` reads only the prerelease's own
  entry, and release admission compares accepted identities, not changelog order.

## Risks / Trade-offs

- One extra `gh release view` call per skipped version. Releases are rarely skipped, and each call
  is bounded by the helper's timeout.
- A transient forge error while checking a version would be read as "not published". The helper's
  error is kept apart from "release not found": any failure other than a missing release refuses
  the journey instead of skipping the version.
