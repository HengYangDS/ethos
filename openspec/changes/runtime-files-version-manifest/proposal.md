## Why

The coupling audit treats any repository containing `pyproject.toml` as an
ETHOS product release workspace. A valid runtime-files adopter therefore enters
product-only release policy, indexes a missing `[project]` table, and emits a
Python traceback from `orient`, `report`, and schema validation.

## What Changes

- Select product release coupling with the existing product-root predicate,
  not file-name coincidence.
- Read runtime-files identity from one repository-owned `[tool.<name>]` table
  and its declared version file when release policy is requested directly.
- Return a structured version-manifest gap for malformed metadata rather than
  raising an implementation exception.
- Return a structured release-config gap when `.ethos/release.toml` cannot be
  decoded instead of leaking the parser exception through an audit command.
- Add a focused adopter regression and update the adoption contract.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `adapters`: subject=runtime-files-version-manifest; reuse=extend;
  change=modify; facet:lifecycle=adoption,validation;
  facet:surface=repository,cli,test,docs,openspec;
  facet:authority=source,test,openspec,docs. Adopter audits remain profile
  bounded while runtime-files release identity is represented without a
  synthetic Python package declaration.

## Impact

- `packages/ethos/src/ethos/repository/policy/coupling/release.py`
- `packages/ethos/src/ethos/repository/release/core.py`
- `tests/unit/release/test_policy_attestation.py`
- Adoption documentation and adapter specification

## Out Of Scope

- Changing ETHOS product workspace metadata or attestation semantics.
- Inventing a universal release schema for every adopter distribution.
- Adding `[project]` metadata to runtime-files repositories.
- Foreign Work Lane mutation, remote publication, or hosted-CI claims.
