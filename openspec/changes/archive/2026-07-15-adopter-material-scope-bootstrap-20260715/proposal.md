# Bootstrap Material-Scope Declarations for Existing Adopters

## Why

ETHOS now requires every adopter profile to declare material paths and binds
those paths to an official OpenSpec Change companion. Existing adopters created
before that contract cannot add the first declaration: their profile is a
material path, but no declaration exists yet to cover the write.

## What Changes

- Permit one exact prewrite admission for a valid, tracked legacy profile that
  lacks the declaration, bound to exactly one official active Change.
- Keep explicit empty or malformed declarations fail-closed, and reject any
  widened request.
- Require the ordinary Change-local `scope.toml` bootstrap immediately after
  the declaration; this new state is not lifecycle replacement or scope
  coverage.

## Capabilities

- `repository-governance`: subject=adopter-material-scope-bootstrap;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation;
  facet:surface=cli,profile,openspec,test,docs,evidence;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Changing the official OpenSpec schema, admitting multiple paths, accepting
  empty or malformed declarations, or making a profile gate or method package
  carry lifecycle authority.
- Closing, landing, publishing, or retroactively certifying any adopter Change.
