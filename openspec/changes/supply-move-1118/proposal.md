# Proposal

## Why

Two events of 2026-11-18 move the supply of this lane's head.

npm 12.2.3 was published at 00:32 UTC. From that minute the locked npm 12.2.2 is not its
registry's latest release, and the dependency acceptance policy reads the three findings that it
bundles as findings behind the latest release, which block:

- glob 13.0.6, GHSA-3g3m-2fjr-6pw4;
- minimatch 10.2.5, GHSA-g3hv-75wg-m249;
- picomatch 4.0.5, GHSA-fc5q-39xc-vjpf.

The full proof of this lane's head `7913f66bc`, started four minutes after that publication,
stopped at the dependency audit with `unapproved_or_expired_findings`; 27 gates had passed, and
the test and package gates did not start. The hosted runs of the same head had passed the audit
before the publication. No ETHOS head passes its proof until the lock moves or a disposition
applies.

npm 12.2.3 bundles the same three versions: the release lead resolved the lock again for it and
read the bundled entries. So the npm move repairs no advisory. It makes the bundling package its
registry's latest again, and the three findings report as unfixed upstream, which they are. The
accepted requirement "Findings without a stable upstream fix do not block" keeps a fixable
finding blocking "until the supply is upgraded or an exact disposition applies", and the upgrade
is the path that needs no acceptance of risk.

At 01:06 UTC, with the npm move committed, the owner directed that the supply of ETHOS and of
every governed repository move to the latest stable releases. A measure of every pinned source of
this repository at 01:11 UTC found, beside npm: the OpenSpec CLI one minor release behind, one
override, 17 packages of the Python lock, three Mise-locked tools, Mise itself and the supply
image's base. The Node.js and Python runtimes, Go, the other seven Mise-locked tools, the six
pinned GitHub Actions and every other direct npm pin were at their latest stable release.

The OpenSpec CLI stays at 2.0.0 here. Its release 2.1.0 no longer exports `readKeptSharedSkills`
from `core/shared-skill-target.js`, which the configuration reader imports: with 2.1.0 installed
the reader refuses every configuration with `openspec_config_invalid:TypeError`, and its
JavaScript test fails on that. Adapting the reader is product code and a row of its own.

Place in the order: the release head of 0.2.0-beta.11, which the owner decided on 2026-11-17 and
2026-11-18 to move once with the batch and two repairs, and the owner's direction of 2026-11-18
for the supply. ETHOS declares a release age of 0 hours, by the owner's decision of 2026-11-13,
so a release of the same day is admitted.

## What Changes

- `package.json` pins `npm` 12.2.3, declares `packageManager` `npm@12.2.3` and overrides
  `minimatch` to 11.0.9.
- `package-lock.json` moves npm with seven of its bundled packages, the override, and two
  packages that the resolution moves with it (`dompurify`, and `ignore` below `globby`). The
  lock holds 555 entries before and after.
- `uv.lock` moves 17 packages, and `pyproject.toml` moves the floors of the seven direct
  requirements among them (`cyclopts`, `fastmcp`, `filelock`, `platformdirs`, `semver`, `ty`,
  `uv`).
- `.config/mise/config.toml` and its lock move uv to 0.13.9, Syft to 1.57.2 and Grype to
  0.122.0, and the floor of Mise to 2026.11.9. The CI projection policy binds the six
  executables of Mise 2026.11.9 by the digests of its `SHASUMS256.txt`.
- The supply image's base moves to the uv 0.13.9 image by digest. The image is rebuilt from
  this lane's proposal ref and bound, since the locks are its manifest inputs.
- The one disposition of the audit policy, for picomatch 2.3.2, names the new lock's digest. Its
  artifact is the same entry with the same integrity.
- The entry of 0.2.0-beta.11 records the move, and its known open defects name npm 12.2.3.

Held, each for its recorded reason: the OpenSpec CLI at 2.0.0 (above), `complexipy` below 9 (the
decision-density baseline is pinned to 8.x scores), Python 3.15 (outside `requires-python`), and
every prerelease channel.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A supply move changes no requirement, so `skip_specs: true` applies.

## Impact

`package.json`, `package-lock.json`, `pyproject.toml`, `uv.lock`, `.config/mise/config.toml`,
`.config/mise/mise.lock`, `.config/checks/ci-projection/policy.toml`,
`.config/ci/supply/Dockerfile`, `.config/checks/dependency-vulnerabilities/policy.toml`,
`.config/ci/pipeline.cue` with its generated pipelines, one test that names the locked Syft, and
`CHANGELOG.md`. The npm lock ships in the wheel as `ethos/resources/package-lock.json`; npm
12.2.3 and the moved Python packages ship in the product's runtime.
