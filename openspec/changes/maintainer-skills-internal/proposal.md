# Proposal

## Why

`npx skills add HengYangDS/ethos`, the skills.sh installer, scans `.agents/skills/` and offers the
four ETHOS maintainer Skills to anyone who runs it; they guide work on ETHOS itself, not on an
adopter's repository. The converged product form (`product-form-plan`, item N6) marks them
internal. Hiding only those four is not enough: when every Skill it finds is internal, the
installer searches the whole repository and offers the packaged `ethos-repository-work` Skill from
the default branch. That copy can disagree with the ETHOS version a user runs, and the same design
rules out a second owner of a repository's Skill.

## What Changes

- The four maintainer Skills and the packaged `ethos-repository-work` Skill carry
  `metadata.internal: "true"`, so skills.sh discovery offers none of them by default.
- The four maintainer packages' manifests record their new digests.
- `.agents/skills/README.md` says why, and a test requires the flag on every tracked `SKILL.md`.
- The Unreleased section of `CHANGELOG.md` gains a Changed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement names a discovery flag, so `skip_specs: true` applies.

## Impact

Five `SKILL.md` files, four `package.toml` manifests, `.agents/skills/README.md`, one test module
and `CHANGELOG.md`. No product code changes.
