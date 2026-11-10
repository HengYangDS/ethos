# Proposal

## Why

Phase T item 1 starts with one fixture signer owner. Test support creates SSH signers in three
places: `fixture_signer.py` for the process signer, `signature.configure_signer` for an own signer,
and inline keygen and anchor lines in `untrusted_signer_repository`, which also hard-code
`/usr/bin/ssh-keygen`. Each fixture runtime install also resolves the invoking ETHOS build twice,
and each resolution runs `git status` and `ls-files` over the checkout. Measured on an
install-heavy set of 8 modules, installs took 20 % of worker time on a clean tree and 31 to 33 %
on a dirty one.

## What Changes

- `configure_fixture_signer(repo, own=None, *, trusted=True, key_type="ed25519")` creates the
  process, own and untrusted signers through one `_create_signer` and returns the anchor.
  `signature.configure_signer` and the inline keygen and anchor lines are deleted, and their 15 call
  sites move to the owner. Own signers now use the shared principal `fixture@example.invalid`.
- `install_fixture_hook_runtime` resolves the invoking build once per worker, keyed by source root,
  and passes it as `hook_runtime_binding(root, expected_build=...)`. A root whose profile is `ethos`
  keeps `expected_runtime_build`'s own branch.
- Four redundant `git config commit.gpgsign true` lines go, since the owner already sets it.
- `python_tests` falls by 13 line-equivalents; no product or tools file changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Test support changes; no requirement changes.

## Impact

11 test files: `tests/support/fixture_signer.py`, `signature.py`, `runtime_scenarios.py` and 8
call-site modules.
