# Design

## Context

See [proposal.md](proposal.md).

- **The journey.** `qualify` downloads the prerelease and one predecessor, proves the shared
  supply and a full proof on the prerelease, installs the predecessor, and calls `prove_upgrade`
  once. `previous_version` names that predecessor: the first earlier changelog entry whose release
  the forge published.
- **The dispatch.** `ETHOS CI` takes `journey_tag` to run the journey alone, and the journey runs
  the dispatching ref's code. Its `release-journey` job runs on macOS and Linux.
- **The receipt reader.** fbee0c's independent verifier reads, per leg, the predecessor's and
  successor's runtime identities and checks each `assets[<version>].sha256` against that release's
  published `SHA256SUMS`. It accepts a single upgrade leg or legs keyed by tag.

## Goals / Non-Goals

Goals:

- One dispatch can qualify the upgrade and rollback from several earlier releases.
- A named predecessor that is not an earlier published release refuses before anything installs.
- The beta criterion names the predecessors that adopters actually take.

Non-goals:

- Discovering which releases adopters select. ETHOS has no fleet registry, and repository rules
  forbid creating one. Release preparation names the set, from the adopters' own declarations.
- Qualifying interruption recovery or live-consumer-safe uninstall. The receipts keep reporting
  those as `not_qualified`.
- Changing how archives are downloaded or verified.

## Decisions

- **Named predecessors are validated like the default one.** `named_predecessors` takes the
  changelog, the prerelease and the names. Each name must match the prerelease tag form, be a
  changelog entry after the prerelease's own entry, and have a published release. The refusals
  are `release_journey_previous_invalid`, `release_journey_previous_not_earlier` and
  `release_journey_previous_unpublished`, each with the tag. Duplicate names collapse, and the
  result follows changelog order, newest first.
- **Shared legs run once.** The prerelease's cold install and full proof do not depend on the
  predecessor, so they stay single. Each predecessor installs under `previous/<version>` and
  upgrades under `upgrade/<version>`, with its own `XDG_DATA_HOME`, so legs share no host state.
- **The receipt keeps per-predecessor evidence.** `previous` lists the predecessor tags,
  `previous_named` says whether the dispatch named them, and `assets` holds one entry per version.
  `upgrade_and_rollback` maps each predecessor tag to its `prove_upgrade` result.
- **The input reaches the shell through the environment.** The step sets
  `JOURNEY_PREVIOUS: ${{ inputs.journey_previous }}` and runs `--previous "$JOURNEY_PREVIOUS"`, so a
  dispatch value is never spliced into the script. The session splits on commas and validates
  each tag before any download.
- **The criterion follows adopter use.** A new requirement makes a beta's journey start from the
  previous release and from every earlier published release that a governed adopter still
  selects. Release preparation reads those selections from the adopters and passes them as
  `journey_previous`. The named-predecessor rules form a second new requirement, so the three
  modified requirements stay within OpenSpec's length limit.

## Risks / Trade-offs

- Each extra predecessor adds one download, one install and one upgrade leg to both journey legs.
  A predecessor set stays small: the releases adopters still select.
- The receipt's shape changes. The repository has no other consumer of the receipt. fbee0c's
  verifier already reads tag-keyed legs.
- A wrong predecessor set yields a passing journey that still misses an adopter's path. The set is
  reviewable in the dispatch and in each receipt.
