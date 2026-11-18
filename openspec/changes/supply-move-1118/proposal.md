# Proposal

## Why

npm 12.2.3 was published at 2026-11-18 00:32 UTC. From that minute the locked npm 12.2.2 is not
its registry's latest release, and the dependency acceptance policy reads the three findings
that it bundles as findings behind the latest release, which block:

- glob 13.0.6, GHSA-3g3m-2fjr-6pw4;
- minimatch 10.2.5, GHSA-g3hv-75wg-m249;
- picomatch 4.0.5, GHSA-fc5q-39xc-vjpf.

The full proof of this lane's head `7913f66bc`, started four minutes after that publication,
stopped at the dependency audit with `unapproved_or_expired_findings`; 27 gates had passed, and
the test and package gates did not start. The hosted runs of the same head had passed the audit
before the publication. No ETHOS head passes its proof until the lock moves or a disposition
applies.

npm 12.2.3 bundles the same three versions: the release lead resolved the lock again for it and
read the bundled entries. So the move repairs no advisory. It makes the bundling package its
registry's latest again, and the three findings report as unfixed upstream, which they are. The
accepted requirement "Findings without a stable upstream fix do not block" keeps a fixable
finding blocking "until the supply is upgraded or an exact disposition applies", and the upgrade
is the path that needs no acceptance of risk.

Place in the order: the release head of 0.2.0-beta.11, which the owner decided on 2026-11-17 and
2026-11-18 to move once with the batch and two repairs. ETHOS declares a release age of 0 hours,
by the owner's decision of 2026-11-13, so a release of the same day is admitted.

## What Changes

- `package.json` pins `npm` 12.2.3 and declares `packageManager` `npm@12.2.3`.
- `package-lock.json` moves npm and seven of its bundled packages: `@npmcli/arborist`,
  `@npmcli/config`, `read-cmd-shim`, `libnpmdiff`, `libnpmexec`, `libnpmfund` and `libnpmpack`.
  Nothing else moves, and the lock holds 555 entries before and after.
- The one disposition of the audit policy, for picomatch 2.3.2, names the new lock's digest. Its
  artifact is the same entry with the same integrity.
- The CI supply image is rebuilt from this lane's proposal ref and bound, since the lock is one
  of its manifest inputs.
- The entry of 0.2.0-beta.11 records the move, and its known open defects name npm 12.2.3.

Not a whole supply move: no other pin is read or moved. The weekly move belongs to the next
batch.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A supply move changes no requirement, so `skip_specs: true` applies.

## Impact

`package.json`, `package-lock.json`, `.config/checks/dependency-vulnerabilities/policy.toml`,
`.config/ci/pipeline.cue` with its generated pipelines, and `CHANGELOG.md`. The lock ships in the
wheel as `ethos/resources/package-lock.json`, and npm 12.2.3 ships in the product's Node supply.
