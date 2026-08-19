## Context

The repository package declaration and lockfile are the supply-chain authority
for the OpenSpec executable used by ETHOS. The system also has current
documentation and a contract test that still name the previous package
version. Historical archive documents are immutable records and are outside
the current package contract.

## Goals / Non-Goals

**Goals:**

- Make `package.json` and `package-lock.json` agree on the stable 1.9.0
  package from the npm registry.
- Make current documentation, specification text, and executable expectations
  agree with that lockfile.
- Use OpenSpec 1.9's native validation and artifact lifecycle without adding a
  parallel ETHOS workflow.

**Non-Goals:**

- No runtime, lane, proof, or adopter changes.
- No rewriting of archived historical records.
- No new product capability or compatibility alias.

## Decisions

1. **Use the exact stable package.** The dependency remains exact
   `@fission-ai/openspec@1.9.0`; npm's official registry and lockfile integrity
   remain the install authority.
2. **Keep this Change spec-free.** The upgrade changes supply-chain identity,
   current prose, and a test expectation, not observable product behavior.
   OpenSpec's native `skip_specs` marker records that fact instead of inventing
   a fake capability delta.
3. **Preserve history.** References to 1.8.0 in archived Changes remain
   historical facts and are not treated as current requirements.

## Risks / Trade-offs

- **Package behavior may differ between 1.8 and 1.9** → official strict
  validation and the focused archive-transition contract test must pass before
  the Change is archived.
- **Ambient global OpenSpec may differ from the project package** → validation
  is run through the installed package in this worktree and the lockfile is
  checked for the exact registry URL, version, and integrity.

## Migration Plan

1. Update the exact package declaration and lockfile with npm using the npm
   registry.
2. Update current contract/docs/test references.
3. Run `npm ci`, OpenSpec 1.9 validation, and the focused contract test.
4. Archive through the normal ETHOS lifecycle only after all checks pass.
