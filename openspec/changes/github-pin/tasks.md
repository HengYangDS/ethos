# Tasks

## 1. Pin module

- [x] 1.1 Add `tests/unit/release/test_pin.py`. Done when it fails before the module exists and
      covers both declared forms, the options form, both keys together, unreadable text, inexact
      versions, lock entries in formats 3 and 4, an absent platform, an unrecorded provenance, a
      class and an identity for each class, and the class of every changelog version.
- [x] 1.2 Add `src/ethos/repository/release/pin.py`. Done when 1.1 passes and the module imports
      only the standard library and `packaging`.

## 2. Installed layout and tool key

- [x] 2.1 Read the tool key from the declaration, the console from `bin/` and the one runtime
      generation from `runtime/` in the Mise helper. Done when the helper's unit test passes for
      an `http:` table and for the GitHub pin, after failing first.
- [x] 2.2 Strip the local `file://` table and drop its `bin_path`. Done when the table's unit test
      passes and the journey reads the runtime through the helper.

## 3. Journey

- [x] 3.1 Verify every archive by its release's class. Done when the unit test names the `gh`
      arguments for each class, the tag's commit as source digest and no call for `checksum`.
- [x] 3.2 Install through the pin and admit each locked entry before the install. Done when the
      unit rows refuse a lock without provenance, with another digest, with a wheel URL, without a
      platform and in another format, and the helper's test shows the lock read before the install.
- [x] 3.3 Require both rebound locks to be refused. Done when a stand-in Mise whose install passes,
      or fails and leaves the tool, fails the journey with the case's name.
- [x] 3.4 Record the Mise release, classes, lock formats and refusals, and add the classes-only
      option. Done when the receipt rows pass and a classes-only receipt reads `classes_verified`.
- [x] 3.5 Declare `GH_TOKEN` in `system/surfaces.toml` and move the decision-density pin of the
      supply proof to `prove_installed_supply`. Done when the product-boundary and
      decision-density architecture tests pass.

## 4. Documents and budgets

- [x] 4.1 Describe the classes and the class-bound verification in
      `docs/governance/provenance-and-attestation.md` and add the changelog entry. Done when
      Prettier and the prose gate accept both files.
- [x] 4.2 Measure the source budget. Done when product, tests and tools are at most 105, 305 and
      197 line-equivalents above the lane base, or a recorded cut lowers them. Measured on the
      lane's commit `fc3167511`: +105.0, +304.1 and +196.8.

## 5. Lane, hosted and owner tasks

- [x] 5.1 Lane: read `gh attestation verify --help` on the host and on a runner. Done when
      `--signer-workflow`, `--source-ref` and `--source-digest` exist on both. The host's gh
      2.104.0 lists the three; on the runners the journey of run 43659748986 verified three
      releases with them on Linux and macOS.
- [x] 5.2 Lane: pass the proof's local install smoke on the commit of group 2. Done when its shared
      supply stage passes with the console in `bin/`. Passed in the full proof at `c79f3aaf8`,
      which holds that commit: the stage qualified the console entry.
- [x] 5.3 Lane, with network: fetch every release tag, then run the journey session for the
      newest published release with every earlier release from 0.2.0-alpha.29 as predecessors and
      the classes-only option. Done when its receipt reads `classes_verified` and names a class
      for each release; a release whose verification fails joins the unbound data with its unit
      row, and the run is repeated for the releases not yet verified. Run on 2026-11-15 at
      `c79f3aaf8` for 0.2.0-beta.10 and the ten earlier published releases: `classes_verified`,
      ten `attested-main` and 0.2.0-beta.3 `checksum`; none failed.
- [x] 5.4 Lane: register `runtime_pin_ambiguous`, `runtime_pin_invalid` and
      `runtime_pin_lock_invalid` when the gap registry of this batch lands. Done when its static
      test passes.
- [x] 5.5 Lane: pass the precheck and readiness at the lane head. Done when each passes on the
      committed head. Passed at `76510cd54`.
- [x] 5.6 Hosted: run CI on the proposal ref. Done when the install legs pass on Linux and Windows.
      Evidence: GitHub run 43642339317 at `3d5365a65`, three Linux and four Windows legs, each
      with the install smoke passed.
- [x] 5.7 Hosted: dispatch the journey alone on the proposal ref for the newest release, with the
      previous release, 0.2.0-beta.6 and each release that an adopter selects. Done when both
      receipts read `passed` and name the Mise release, format 3 for the prerelease's lock, each
      class and both refusals, each refusal's message names its cause, and the Linux x64 receipt
      lists five platforms. GitHub run 43659748986 at `c79f3aaf8`, with 0.2.0-beta.9 and
      0.2.0-beta.6; every governed repository of this host selects 0.2.0-beta.10 itself. Both
      receipts read `passed`, Mise 2026.11.8, format 3 and `attested-main` for each release. The
      changed checksum is refused as a checksum mismatch, and the foreign entry because its URL
      belongs to another release.
- 5.8 Withdrawn by DR-0016 (superseded). Owner, only if a refusal does not hold: decide the
  narrowed claim and the upstream report. Both refusals held in run 43659748986.

## Workflow follow-up

- The first release after this Change reads its own journey receipt in its release Change: the
  prerelease's class is `attested-main` and both refusals held.
- `release-provenance` records the last release dispatched from `main` in the class data, with a
  unit row for the first release dispatched from its tag.
