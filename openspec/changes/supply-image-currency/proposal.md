# Proposal

## Why

Twice a change to a supply-image input landed without a rebuilt image. The local full proof
passed, then every GitLab job refused at its first step, `sha256sum --check`, and main could not
publish (register rows 11 and 18). Nothing in the repository records which commit the bound image
was built from, so no local check can tell that the bound image is stale.

## What Changes

- The binding records the commit that the bound image was built from, as `gitlabImageSource`,
  beside `gitlabImage` in `.config/ci/pipeline.cue`, in the same edit as the digest.
- The CI projection check, a gate with no dependencies, reads the manifest's input list from the
  Dockerfile. For each listed path it compares the working tree's SHA-256 with the path's bytes at
  `gitlabImageSource`. A difference refuses with `supply_image_stale:<path>` and names the route:
  rebuild the image on the proposal ref, then bind it.
- GitLab's bootstrap tool list is derived from the Dockerfile's list, so the two cannot diverge.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a stale supply image is refused before any proof gate runs.

## Impact

- `.config/ci/pipeline.cue`, `tools/ci/ci_projection.py` and their tests.
- Out of scope: reproducible image builds, and deriving the digest from the inputs. The digest
  exists only after the hosted build.
