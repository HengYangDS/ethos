# Proposal

## Why

The docs registry still reads metadata that a document under the docs root wraps in a leading HTML comment. It does so for compatibility until no adopter tracks such a document. The accepted `repository-governance` requirement already states that such a document declares no metadata, and the repository paradigm reports the wrapper with its repair. No governed repository's development line or active Work Lane now tracks a wrapped document. That is the restore condition DR-0016 recorded for task 2.16 of `legacy-carrier-retirement`, which this Change restores.

## What Changes

- **BREAKING** for a repository that still wraps its metadata: the docs registry, decision records and docs health read plain front matter only, so a wrapped document declares no metadata and reads as missing. `ethos lane repair-paradigm --apply` removes the wrapper.
- The `docs_title_not_first` gap retires with the carrier, because plain front matter leaves no hidden declaration ahead of the title.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. This Change implements behavior that accepted requirements already specify: `repository-governance` "Structured documentation metadata preserves meaning" in its scenario "Selected documentation renders its title before metadata", and `repository-paradigm` "Documents carry YAML front matter".

## Impact

Code: `src/ethos/repository/registry/docs/` (registry, health and decisions), `src/ethos/repository/design/integrity.py`, `src/ethos/repository/audit.py` and their tests. Docs: `docs/governance/docs-registry.md` and `CHANGELOG.md`. Out of scope: OpenSpec, Skills and system-axiom syntax, and the paradigm repair, which keeps reporting and removing the wrapper.
