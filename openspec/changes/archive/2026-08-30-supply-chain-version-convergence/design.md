## Context

See proposal.md for motivation. `VERSION` is already the single product-version
owner, and package/runtime identities already bind source commit/tree and
artifact digests. The OpenSpec adapter already derives its required version
from the root npm declaration and lockfile. The defect is stale authority
values and release history, not a missing mechanism.

## Goals / Non-Goals

**Goals:**

- Advance the existing product-version owner and all checked projections.
- Advance the existing exact OpenSpec dependency and all current supply
  projections with verified stable releases.
- Make source, built package, installed runtime, and CLI observations agree.
- Preserve a concise Keep a Changelog history for alpha.2 and alpha.3.

**Non-Goals:**

- No new version registry, compatibility layer, or runtime identity field.
- No CLI grammar, tempfile lifecycle, adopter migration, or publication change.
- No new dependency, compatibility line, or host-managed runtime mutation.

## Decisions

1. **Change existing owners only.** `VERSION` remains the product SemVer owner;
   npm manifests remain derived projections; package/lock data remain the
   OpenSpec supply owner. Adding another version carrier would duplicate
   authority.
2. **Use exact OpenSpec 1.11.0.** The npm `latest` tag was verified as 1.11.0 on
   2026-08-30. The repository continues exact pinning rather than introducing a
   range or ambient resolver.
3. **Use `0.2.0-alpha.3`.** This is the smallest SemVer-forward prerelease that
   distinguishes the new product semantics from alpha.2. Exact source and
   artifact identities continue to distinguish individual development builds.
4. **Regenerate lock data with npm.** Package manager output, not manual hash
   editing, owns integrity and transitive metadata.
5. **Keep compatibility distinct from currentness.** The Node policy retains
   one current LTS and one current release, while historical version fixtures
   remain test data rather than active supply. Python and npm locks advance only
   declared direct dependencies; transitive changes remain resolver-owned.

## Risks / Trade-offs

- **OpenSpec 1.11 behavior differs from 1.10** → run official strict validation,
  archive rehearsal through product tests, and the repository OpenSpec gates.
- **A version projection remains stale** → retain focused owner/projection,
  CLI, build, install, and runtime identity checks before full proof.
- **A dependency update changes behavior** → run the full repository gate set
  once at the frozen candidate boundary and revert the exact update rather than
  add a compatibility layer.
- **The changelog overstates release publication** → mark alpha.2 as a dated
  repository product release record while leaving alpha.3 changes Unreleased;
  do not claim remote package publication without separate evidence.

## Migration Plan

Update the official Change and regression expectations first, advance the two
existing authorities and generated lock projection, run focused through
installed-runtime verification, then commit, prove the exact HEAD, archive the
Change, prove again, and promote through the public candidate/accepted path.
Rollback is the exact Git parent before promotion; no compatibility state is
created.
