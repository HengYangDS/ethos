# Proposal

## Why

Governed repositories reported three counterexamples on 2026-10-31, each measured on the
0.2.0-alpha.23 release.

- **Windows path length.** The GitLab Windows ARM64 jobs of data-department-work-guidelines fail
  with "exit status 6". Their install root is 157 characters: the GitLab build directory, the
  job-local Mise data directory and Mise's install directory. The release archive adds
  `ethos\runtime\<64 hex digits>\python\python.exe`, 96 characters, so the interpreter path is 253
  characters. On the CI guest Windows ran the interpreter at 236 characters, failed it at 240 and
  244, and refused to start it from 248 with `STATUS_NAME_TOO_LONG` (`0xC0000106`), whose low byte
  the job reports as status 6. Enabling `LongPathsEnabled` did not change the start.
- **Published archive compensation.** A Work Lane archived its Change, published the archived head
  as a proposal and then compensated the archive. The proposal ref kept the archived commit, which
  no owned ref then retained, so proposal retirement refused and the ref could only be retired after
  its review closed.
- **Frozen carriers and the code ceiling.** A film repository keeps a render input whose SHA-256 the
  final production manifest binds and a proof gate verifies. Its format selection declares the file
  a byte-bound carrier (`format_owner = "immutable-carrier"`, `mutation_policy = "forbidden"`), so
  no formatter or edit may change it. The code ceiling still measures it, which leaves two ways to
  conform: a split that voids the evidence the bytes are bound to, or a higher whole-repository
  ceiling that also covers every mutable file.

## What Changes

- The release archive names its runtime directory with the first 16 hexadecimal digits of the
  runtime digest, so the interpreter path inside the archive is 48 characters on Windows. A test
  bounds that path at 64 characters. An archive carrier resolves the prefix to the full digest from
  the runtime manifest; the host store and its selectors keep the full digest.
- Archive compensation refuses while a recorded publication selects the archived head, with
  `openspec_archive_published:<change>` and the proposal retirement as the next action, which still
  succeeds because the Work Lane retains the head.
- The paradigm receives a tracked file that the repository's format selection declares a byte-bound
  carrier verified by one of its proof gates, as it receives vendored and generated files: the code
  ceiling does not measure it and its name keeps its form. An invalid declaration receives nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the Windows runtime archive fits the Windows path limit.
- `repository-governance`: compensation refuses a published archive.
- `repository-paradigm`: byte-bound carriers are outside the code ceiling.

## Impact

- `tools/ci/delivery/distribution.py` and the runtime selection, resolution, version, authority,
  materialization and acceptance modules that read an archive's runtime directory.
- `src/ethos/adapters/mutation/lane_lifecycle/archive/compensation.py` and
  `src/ethos/adapters/repo/attestation_lifetime.py`.
- `src/ethos/adapters/gates/native/inputs.py`, `src/ethos/domain/status.py`,
  `src/ethos/repository/audit.py`, `src/ethos/repository/paradigm/report.py` and
  `src/ethos/adapters/mutation/paradigm_repair.py`.
- Out of scope: Windows hosts whose install root is so deep that imports from the runtime exceed the
  Windows path limit still need long paths enabled; the cel-expr-python wheel's packaged build tree
  is reported upstream.
