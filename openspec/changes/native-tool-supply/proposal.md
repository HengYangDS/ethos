## Why

Verify job 37512 reaches scanner preparation but cannot write `/usr/local/bin`.
The preceding repair exposed rather than removed the installer's ambient root
privilege assumption. Native tool supply must be project-owned and must behave
identically in local, hosted and non-privileged environments.

## What Changes

- **BREAKING** Replace the separate SCC and gitleaks installer scripts with one
  native archive materialization owner; callers receive exact cache directories.
- Keep versions, platform archive digests and release coordinates in their
  existing tool-native configuration. Add the official macOS scanner digests.
- Validate archive members, executable bytes and version; serialize identical
  cache effects, atomically replace only the selected executable, and discard
  owned scratch on success or failure.
- Make proof and secret-scanning entrypoints use the same owner, with no global
  install, administrator request, ambient binary fallback or new tool registry.
- Preserve official requirement renames as exact source/destination relations in
  the existing Commitment compiler. Native validation passed but the incumbent
  compiler blocked this Change and its own repair; bounded recovery is recorded.
- Close the test-evidence prerequisite exposed by this batch's interrupted full
  proof: invalidate prior completion before work, isolate partial results, and
  preserve external referents during cleanup. Project the verified discipline
  through the existing quality Skill, not a new feedback or execution system.

## Capabilities

### Modified Capabilities

- `quality`: native verification tools are materialized in controlled local
  storage without privileged installation, and validated before tests execute.
- `contracts`: official rename intent compiles without fabricated requirements
  or treating a rename-only Change as spec-free.

## Impact

`tools/ci/toolchain/native.py`, `tools/ci/scripts/install-scc.sh`,
`tools/ci/scripts/install-gitleaks.sh`, `tools/ci/scripts/run-head-bound-proof.sh`,
`tools/ci/scripts/run-secrets-scan.sh`, `.config/checks/secrets/supply.toml`, the
existing native-supply/hosted tests, quality specification, configuration
explanations and terminal plan.
The necessary governor repair changes `src/ethos/adapters/openspec/commitment.py`
and its existing compilation regression module; no new authority is introduced.
The proof-integrity repair stays in `tools/ci/python_test_gate.py`, its existing
regression module and the quality Skill. Automatic strong-kill resource recovery
remains outside this bounded correction and is not claimed complete.

## Non-Goals

No repository runtime lifecycle, package manager, compatibility wrapper, adopter
mutation, new global configuration or broader tool migration. Existing download
transport remains separate; this owner consumes it within isolated preparation.
