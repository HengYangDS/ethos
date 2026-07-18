# CI Verify Local Emulator Optional Tool Boundary

## Why

Hosted `ethos:verify` runs the repository-owned Python test gate inside the
GitLab runner image. Local provider emulator tools such as `gitlab-ci-local` are
adapter tools, not repository truth and not required for hosted verification of
repository semantics. A `doctor` observation of a local emulator should still
emit bounded local evidence when the optional emulator binary is absent, while
materializing emulator runs must remain fail-closed.

## What changes

- Distinguish observation modes (`doctor`, `list`, `dry-run`) from materializing
  emulator run modes.
- Allow observation-mode local emulator evidence to report `tool_available=false`
  without failing hosted verification.
- Keep materializing emulator runs fail-closed when the provider tool is missing.
- Load the CI owner script in architecture tests by file path so tests do not
  depend on `tools/` becoming a Python package truth center.
- Cover both branches so the 100% coverage owner gate remains deterministic.
