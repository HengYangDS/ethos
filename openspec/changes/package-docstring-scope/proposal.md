# Proposal

## Why

The rule that a package states its purpose in a docstring arrived blocking in 0.2.0-beta.10, with
no earlier report and no repair that the product can write. It reports since 0.2.0-beta.11
(`reporting-obligations`). Two questions were left for the owner, after the stable release:
which package markers owe a docstring at all, and when the rule arms again.

Measured in governed repositories:

- One repository's required gaps went from 791 under 0.2.0-beta.7 to 2,144 under 0.2.0-beta.10.
  The whole increase was this rule, 1,348 rows, and 5 rows of another rule. 577 of the rows were
  in a tooling package, 415 in tests, the rest in product packages and examples.
- On disposable copies under the candidate of 0.2.0-beta.11 the rule moved from required to
  reported and no other code changed: required 2,350 to 882 with 1,468 reported in one
  repository, and 843 to 640 with 203 reported in another.
- The selector treats every package marker as an authored package. 933 of the 1,348 rows lie
  outside that repository's tests, so a narrower selector alone would not clear it.

The committee's recommendation of 2026-11-14: the scope is the marker of an importable package
under a module's source root, decided on the path classifier; the rule arms again no earlier than
one release after its repair and its preview ship and ETHOS itself reads zero; no date now.

## What Changes

- The rule's scope is stated once, by the path classifier.
- A repair with a preview that lists the markers by tree.
- The rule arms again by a release that names it, one release after the repair ships.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The paradigm's package rule, its selector and the paradigm repair. Arming it again is a rule
change and follows the order after the stable release.

Owner: the release lead; the scope and the arming are the owner's decision. Next action: none
before the stable release. Read again: after 0.2.0.
