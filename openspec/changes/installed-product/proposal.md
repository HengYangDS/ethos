## Why

The accepted product exposes repository-bound runtime commands but does not yet
provide the independent CLI/MCP experience required by the terminal contract.
Application results are composed inside CLI handlers, preventing a second
transport from reusing behavior without importing presentation or parsing stdout.

## What Changes

- Extract existing application operations once and make CLI and SDK direct consumers.
- Deliver the required installed stdio MCP surface using FastMCP over the official SDK, with
  explicit repository and actor binding, structured results and bounded failures.
- Separate reusable host installation from repository-selected immutable supply;
  preserve current policy, exact source identity and fresh effect admission.
- Deliver Homebrew installation and portable, version-matched Skills/context;
  distinguish distribution channels from the package builder.
- Prove clean installation, real client use, cross-repository isolation,
  interruption, upgrade, rollback and exit before retiring replaced runtime paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: shared typed application operations and discoverable MCP transport.
- `repository-governance`: shared accepted-contribution observation and separately
  admitted local closure after remote proposal retirement.
- `distribution`: independent installation and explicit repository version selection.

## Impact

Existing command composition, distribution/runtime selectors, native package
metadata, their tests and the canonical terminal plan. MCP SDK replaces custom
protocol handling; no broker, background daemon, second lifecycle, task database,
adopter mutation or new work lane. Remaining quality repairs stay in their
existing Change and are not all prerequisites for this delivery.
