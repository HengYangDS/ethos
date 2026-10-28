# Proposal

## Why

GitHub ruleset 25827049 protects `dev` and `main` with 12 required checks. Nine of them, `<os> / Python <v>`, never match a check run, because `.config/ci/pipeline.cue` names the host conformance jobs `<os> / Python <v> / Node <version>` (since `41a75140c`, 2026-10-05). A pull request therefore can never satisfy the ruleset, and each Node supply bump would rename all nine checks again. The owner asked on 2026-10-28 to fix this at its root.

The root is the job identity, not the ruleset. A supply version is a property of what a job runs, so it does not belong in the name a forge requires.

## What Changes

- **Job identity.** The host conformance job is named from its matrix coordinates alone: `${{ matrix.os }} / Python ${{ matrix.python }}`. The locked Node version still selects the runtime through mise, as before.
- **Projection.** The generated GitHub workflow follows; the GitLab projection is unchanged, since its jobs have no matrix.
- **Regression.** Each projected job's name is a function of its matrix coordinates on both forges, which replaces the old check that the name carried the Node version.
- **Specs.** quality adds the requirement that hosted check names are stable identities.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: hosted check names are stable identities.

## Impact

- The ruleset needs no change: its nine contexts match the renamed checks from the first hosted run of this Change. The owner's own pushes still bypass the pull-request rule, which design decision D6 keeps as the maintainer route.
- `forge-admission-and-assurance` (design revision 5.1, D6) will derive the required contexts from `pipeline.cue`, so the declaration and the names cannot drift apart again.
- No product Python changes; one test asserts the new identity.
