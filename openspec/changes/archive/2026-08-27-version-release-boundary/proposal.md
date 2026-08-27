## Why

The accepted Git root is incorrectly treated as an explicit package release.
That makes a previously released product version block installation of newer
accepted source and lets ordinary hook installation mint release evidence.
The changelog also does not describe the current prerelease line consistently.

## What Changes

- Keep `VERSION` as the single SemVer product-version authority and advance the
  next target to `0.2.0-alpha.2`.
- Make every source-checkout build a unique PEP 440 development build,
  regardless of Git branch role.
- Remove `channel` and `acceptance_state` from durable build/runtime identity.
- Admit an exact release identity only through an explicit release transition.
- Upgrade the runtime manifest directly and reject the retired shape.
- Reconcile `CHANGELOG.md` with Keep a Changelog and SemVer terminology without
  claiming unpublished tags or remote releases.

## Impact

Build identity, package metadata, runtime manifests, release admission,
hook/runtime status, tests, release documentation, npm projections, and the
OpenSpec distribution contract change. No adopter repository changes.
