# Quality Capability Portfolio Convergence

## Why

ETHOS has a broad tool catalog, but active gate wiring, documentation facts, and
future-tool decisions are not yet one MECE capability portfolio. That permits
owner-script bypass, unproved active tools, stale scanner names, standard-name
overclaim, and repeated proposals for heavy or overlapping platforms.

## What Changes

- Repair the selected active import-boundary and dependency-hygiene chain from catalog
  through owner script, gate registry, and default/full proof sets.
- Validate the tracked pre-commit configuration through the existing config
  owner gate and a locked project development dependency.
- Make vulnerability, SBOM, provenance, and attestation descriptions match the
  implementations actually executed today.
- Keep admitted active mechanisms in the runtime catalog and record one ranked
  roadmap decision per relevant quality capability: active, bounded pilot,
  deferred on-demand, or rejected.
- Require every pilot to end in promotion, absorption-and-retirement, or
  rejection; permanent external/native dual implementations are forbidden.

## Out Of Scope

- Installing or activating the newly selected pilot tools in this Change.
- Recompiling every local/hosted execution plane from `system/gates.toml`,
  relocating installer behavior out of owner gates, or repairing every existing
  tool-supply checksum in this Change; these are the first follow-up wave.
- Adding SonarQube, a cloud AppSec dashboard, telemetry backend, external
  autofix bot, release manager, or another command plane.
- Remote publication, hosted CI success, release signing upload, or historical
  Work Lane cleanup.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: subject=quality-capability-portfolio-convergence; reuse=extend;
  change=modify; facet:lifecycle=validation,release; facet:surface=cli,config,
  docs,openspec,evidence,ci,test; facet:authority=source,test,schema,docs,
  openspec,claim,evidence.

## Impact

The Change modifies the existing quality catalog, gate registry, config owner,
quality specification, release-standard descriptions, roadmap, tests, and
evidence carriers. It adds no runtime dependency, service, compatibility layer,
wrapper command, or parallel quality implementation.
