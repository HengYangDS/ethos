# Proposal

## Why

On 2026-11-12 the owner decided that ETHOS takes vulnerability reports privately (decision D3 in
`product-form-plan`), and GitHub's private vulnerability reporting was enabled for the repository
the same day. Nothing in the repository says so: there is no `SECURITY.md`, so a reporter finds no
private route, no scope and no statement of which releases receive fixes. The repository paradigm
has admitted a root `SECURITY.md` since 0.2.0-beta.8.

## What Changes

- A root `SECURITY.md` names the private route (GitHub's **Report a vulnerability**), gives
  examples of what to report, lists the product's documented limits that are not vulnerabilities,
  states the best-effort handling of a project with one maintainer, and says that only a new release
  carries a fix.
- The Unreleased section of `CHANGELOG.md` gains an Added line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The paradigm catalog already admits the file, and no requirement changes.

## Impact

`SECURITY.md` (new) and `CHANGELOG.md`. Product code is unchanged.
