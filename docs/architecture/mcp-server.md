---
subject: ethos:mcp-adapter
role: explanation
state: canonical
relations:
  canonical_for: MCP adapter boundary
---

# MCP Adapter

Status: canonical.

Purpose: define MCP as a replaceable projection over repository truth.

See also: [Agent Projections](agent-projections.md) and
[Command Plane](../reference/command-plane.md).

MCP is a required Agent-facing product surface, not another lifecycle or authority.
The standalone CLI and MCP adapter invoke the same application operations with an
explicit repository, actor, inputs and current admission. Repository intent, Git
facts, Lease coordination and Attestations keep their existing owners.

The first local transport is stdio through the installed product, using the official
MCP SDK. Protocol output is isolated from diagnostics. A network transport is an
optional deployment boundary requiring explicit authentication and authorization;
a local client does not require a broker or a permanent system daemon.

Tools and resources expose discoverable schemas, bounded execution, cancellation,
structured failures and resumable operation identities. Client-supplied actor
labels or an earlier successful check never grant mutation authority. Each effect
rechecks current authorization and exact repository facts at the existing owner.

The installed stdio server uses locked standalone FastMCP over the official SDK
with strict input validation and framework tasks disabled. It registers the
existing typed status, plan, adopt, land and publish operations without its own
parser or task store. Real-client conformance remains unqualified: it requires
initialization and capability discovery, read-only and admitted mutation
journeys, denied and unknown outcomes, cancellation and recovery, repository
isolation, upgrade and uninstall. The kernel being callable without MCP does not
make the full product complete.
