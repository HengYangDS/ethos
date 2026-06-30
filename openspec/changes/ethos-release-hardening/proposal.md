## Why

ETHOS must govern itself with the same rigor it applies to adopter
repositories. The current product still has three gaps: package-root forwarding
wrappers, incomplete official OpenSpec artifacts for self-governance, and
GitLab-visible release/signature readiness that is not distinguished from local
Git signature verification.

## What Changes

- Remove package-root re-export shells and require imports from semantic
  modules.
- Keep OpenSpec as an official self-governance capability under `openspec/`,
  with complete proposal, design, specs, tasks, and official CLI validation for
  this batch.
- Add release policy, SBOM, and in-toto/SLSA-shaped release attestation
  projections.
- Add history identity audit so raw commit metadata and service-side signature
  verification are treated as explicit release gates.
- Add agentic context bundle projection for MCP/ACP consumers without making
  host-local agent state authoritative.

## Capabilities

### New Capabilities

- `release-governance`: Release policy, attestation, SBOM, tag, and history
  identity readiness for ETHOS itself.

### Modified Capabilities

- `ethos-kernel`: Clarify that official OpenSpec artifacts are self-governance
  planning records for ETHOS, while the public command plane remains rooted at
  `ethos`.

## Impact

Affected areas include package imports, CLI quality commands, governance
modules, agent context projections, OpenSpec artifacts, release docs, and tests.
