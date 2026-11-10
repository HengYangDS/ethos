# Proposal

## Why

Measured at `42b08a1ca`, 16 groups of identical function bodies exist in `src/` and `tools/`: 58
definitions where 16 owners suffice, every group across modules. The test compares bodies after
renaming parameters and locals and keeps the names a body reads. Among them:

- 31 refusal aliases (`_fail`, `_invalid`, `_require`, `require_release`,
  `_file_observation_failure`), five of them annotated `-> None` although they always raise;
- 7 file digests, 3 stream decoders and 2 strict coercion pairs;
- 2 copies of the Lease verdict, 2 PEP 503 name normalizers and 2 identical model digest methods;
- 3 validators in `tools/ci/format_selection.py` copied from the policy module it already imports,
  beside 2 copied glob matchers that nothing called.

No gate refuses a second implementation, so each new module added its own.

## What Changes

- The kernel owns each behavior once: `refuse` and `require` beside `refusal` in
  `ethos.contracts.outcome`; `file_sha256` in `ethos.contracts.digest`; `model_digest` beside
  `canonical_json_digest`; `lease_verdict` in `ethos.contracts.verdict`; `required_mapping` and
  `required_sequence` in `ethos.normalization.coercion`.
- Every duplicated alias is deleted and its callers use the owner; helpers that share a name but
  not a body stay. A refusal is now an `OutcomeError`, which is a `ValueError` with the same
  message.
- `ethos.adapters.process.stream_text` is the one stream decoder, and
  `packaging.utils.canonicalize_name` the one PEP 503 normalizer.
- `tools/ci/format_selection.py` imports the policy module's 3 validators and drops the 2 unused
  matchers.
- A new architecture test refuses any two identical function bodies of 4 or more syntax nodes in
  `src/` or `tools/`, with no allowlist. A script the hosted CI runs without the project environment
  cannot import an owner: its scope comes from the CI workflow, and a second test requires it to
  import only the standard library.
- The single-gap check also covers `refusal` itself.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The behavior of every command is unchanged.

## Impact

61 files under `src/`, `tools/` and `tests/`. No public command, result or configuration
changes.
