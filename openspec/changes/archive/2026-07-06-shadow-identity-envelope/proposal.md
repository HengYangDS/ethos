# Shadow Identity Envelope

## Why

External ETHOS retirement readiness depends on a stronger claim than generic
command parity. The product must prove that external and embedded backends are
compared against the same repository, same HEAD, same changed paths, and same
evidence inputs. The existing shadow parity report compares structured command
outputs, but the input identity was not first-class in the report or schema.

## What Changes

- Add a shadow identity envelope to executed shadow parity reports.
- Include target root, target HEAD, product HEAD, changed paths, command lists,
  external/embedded command identities, and evidence input digests.
- Persist the identity envelope into tracked parity evidence.
- Update the shadow parity schema and contract sample so validation gates enforce
  the new shape.
- Clarify that tracked parity evidence lives under `evidence/parity/`.

## Capabilities

### Modified Capabilities

- `ethos-repository`: subject=shadow-parity-identity-envelope; reuse=extend;
  change=modify; facet:lifecycle=validation,runtime;
  facet:surface=cli,schema,docs,openspec,test,evidence;
  facet:authority=source,test,schema,docs,openspec,claim,evidence

## Out of Scope

- No adopter-specific product ontology, package, or fixture directory is added.
- No reference-adopter embedded backend is retired by this change.
- No rollback-window, domain false-negative suite, or remote publication gate is
  claimed complete by this change.

## Impact

- Affected code: shadow parity adapter and tracked parity evidence builder.
- Affected schema: `system/schemas/kernel/shadow-parity.schema.json`.
- Affected tests: product parity and schema validation tests.
- No adopter-specific directories, reference-adopter-specific product fixtures, remote
  publication, or embedded retirement is performed by this change.
