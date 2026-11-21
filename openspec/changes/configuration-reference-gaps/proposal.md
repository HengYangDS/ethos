# Proposal

## Why

Governed repositories met two rules of configuration that no reference page states:

- **The carrier role.** A Git attribute, `ethos-role`, gives a tracked carrier one of nine roles,
  and only an unset role, `code` and `generated` owe behavior evidence. No page under `docs/`
  names the attribute, and ETHOS's own attributes file uses it twice. One repository met 323
  files that asked for evidence before it found the attribute in the source.
- **The import path of a test carrier outside the root.** With an explicit configuration file,
  pytest 9.2.0 resolves `pythonpath` against that file's directory and does not normalise it, so
  modules import under paths that hold parent segments. The ruling of 2026-11-14: such a carrier
  declares no `pythonpath`, the environment owns the import path, and commands run from the root.
  One repository measured 3,904 equal node identities under it.

A third is a procedure: renaming a release branch runs through the native rename inside a
landing; the new name is protected on a peer before its first push, and the old name leaves the
forge last.

## What Changes

- The configuration reference states the carrier role, its nine values and which of them owe
  behavior evidence.
- It states the import-path rule for a test carrier outside the root.
- The release guide states the order of a release branch's rename.
- ETHOS's own pytest carrier drops its `pythonpath` only after a whole-suite run shows equal node
  identities and import paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`docs/reference/configuration.md`, the release guide and one key of ETHOS's own pytest carrier. No
rule changes.

Owner: the release lead. Next action: write the reference lines; run the equivalence for the
carrier key. Read again: at the cut of 0.2.0-beta.12.
