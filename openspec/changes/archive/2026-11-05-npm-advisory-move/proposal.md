# Proposal

## Why

npm 12.2.2 was published at 2026-11-04 23:02 UTC. It bundles undici 6.29.1 and ip-address 10.7.5,
which fix six of the eight advisories that ETHOS's shipped npm 12.2.1 carries:

- undici: GHSA-2m5v-pch6-74hx, GHSA-4qv8-2p9j-2685, GHSA-9fm3-97px-rjf6, GHSA-qrxm-fqhp-jwvm and
  GHSA-xjj6-f33q-929c;
- ip-address: GHSA-rxp7-6hxx-x8q5.

Once a fixing release exists, the dependency acceptance policy blocks every shipped finding that it
fixes. The two remaining advisories are in glob 13.0.6 and minimatch 10.2.5, and 12.2.2 still
bundles those versions. They block too, because the bundling package is no longer its registry's
latest release. So since that release, no ETHOS head passes its proof.

The 24-hour release-age rule would hold 12.2.2 until 2026-11-05 23:02 UTC. On 2026-11-05 the owner
decided to take it now: the fix removes known vulnerabilities from what ETHOS ships.

## What Changes

- `package.json` pins `npm` 12.2.2 and declares `packageManager` `npm@12.2.2`.
- `package-lock.json` moves npm and seven of its bundled packages: `@npmcli/promise-spawn`,
  `bin-links`, `ip-address`, `libnpmexec`, `pacote`, `semver` and `undici`. Nothing else moves.
- The `0.2.0-beta.2` entry records the move, the advisories it fixes, the two that remain unfixed
  upstream, and the exception to the release-age rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A supply move changes no requirement, so `skip_specs: true` applies.

## Impact

`package.json`, `package-lock.json` and `CHANGELOG.md`. The lock ships in the wheel as
`ethos/resources/package-lock.json`.
