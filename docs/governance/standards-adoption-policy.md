---
subject: ethos:standards-adoption
role: decision
state: canonical
relations:
  canonical_for: standards adoption
---

# Standards Adoption Policy

ETHOS adopts mature standards before inventing formats.

Adoption levels:

- Native standard: the standard shapes ETHOS protocol output.
- Attestation envelope: the standard wraps ETHOS evidence without owning it.
- First-class adapter: the framework can execute or sign projections.
- Artifact metadata adapter: the framework projects package or SBOM facts.
- Event interchange adapter: the framework exports Chronicle or gate events.
- Advanced compiler: the framework generates ETHOS-native config or schemas.
- Service runtime adapter: the framework runs long-lived workflows outside CLI core.
- Agent projection: the framework exposes ETHOS context to agent hosts.

Every adapter must declare lifecycle, boundary, input contract, output contract,
fallback, and exit strategy before it can be treated as product capability.

The first adapter set covers SLSA provenance, in-toto attestations, Sigstore
signing, SPDX SBOM projection, CDEvents, OpenTelemetry semantic events, Dagger
runner projection, CUE profile compilation, OPA policy decisions, Temporal
service runtime, and MCP agent projection.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
