# Proposal

## Why

`documents-within-ceiling` moved the command plane's "Hidden Operational Roots" section into its own
reference, `docs/reference/operational-roots.md`, and left a link to it in the command plane. The
wheel ships the command plane as an installed resource, but not the new reference: `pyproject.toml`
names each installed document, and the Change did not add it.

The full proof of the lane head `606ad77da` stopped on
`test_installed_navigation_preserves_required_links_without_source_checkout`. In the installed
package, the link `docs/reference/command-plane.md -> operational-roots.md` does not resolve, so an
installed ETHOS would lose the operational-roots text that its command plane carried before the
split.

## What Changes

- The wheel's `force-include` and the sdist's `only-include` in `pyproject.toml` add
  `docs/reference/operational-roots.md` beside the command plane, which they already ship.
- No document, requirement or measure changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The installed document set is a packaging declaration; `skip_specs: true` applies.

## Impact

`pyproject.toml` changes, and the wheel and sdist ship one more document. No lock changes, and the
GitLab supply image's hashed inputs do not include `pyproject.toml`.
