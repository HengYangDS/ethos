# Proposal

## Why

The release-candidate plan gives a workstation a fast tier: what the full proof and the forges
would say, learned in minutes. Three facts of 2026-11-15 belong to its acceptance:

- A change to a document selected no test, because selection followed imported modules. A link
  added to a page that an installation carries failed a test on the forge first. The release
  lane's own tool now selects the tests that name a changed path or stage the package.
- Five sessions run only on the forges, and nothing lists them for a workstation.
- One governed product's session met 16 problems in eight hours. Twelve were found late, and each
  of the twelve had a check of less than two minutes.

## What Changes

- A changed data file selects its readers: the tests that name its path, and the tests that stage
  the installed package when the package carries it.
- The tier lists the sessions that a workstation cannot run, so that a pass does not read as the
  forges' pass.
- The tier's result names what it did not examine.
- The tier runs the root-cache check of the repository audit. On 2026-11-15 a cache directory
  that Git ignores failed readiness 80 minutes after the command that made it, while the tree
  read as clean.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The fast tier's selection and its result. It adds no refusal.

Owner: the release lead. Next action: converge the design and measure the patch. Read again: at
the cut of 0.2.0-beta.13.
