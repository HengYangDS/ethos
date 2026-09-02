## Why

GitLab executes the complete repository proof after dropping pytest to an
unprivileged identity, but the resulting process tree does not receive one
complete, locked execution supply. The same accepted commit therefore passes
the other hosted planes while GitLab reports 132 failures caused by missing
native process observation, leaked run-as control inputs, a relative offline
cache, and one test fixture that substitutes an ambient OpenSpec command.

## What Changes

- Require each hosted proof job to supply every declared native executable
  before the proof process starts.
- Compile the pytest child environment once at the privilege boundary: consume
  run-as inputs there and project repository-owned caches as absolute paths.
- Require nested tests and builds to inherit the locked execution supply rather
  than reinterpret control inputs or resolve tools from ambient `PATH`.
- Replace the ambient OpenSpec test double with the existing source-bound
  resolver.
- Preserve local, GitLab, and GitHub as distinct evidence planes; do not weaken
  offline execution, warnings-as-errors, identity isolation, or exact-HEAD
  proof.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: make the capability-preserving test floor include a complete,
  locked execution supply across privilege and nested-process boundaries.

## Impact

The hosted Linux bootstrap, Python test execution owner, and their focused
architecture/unit tests change. Provider YAML remains a projection of those
owners. No new schema, registry, wrapper, compatibility path, persistent cache
authority, or adopter carrier is introduced.
