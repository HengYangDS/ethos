## Context

ETHOS is a repository-evolution product, not an architecture-publication
integration. Runtime independence alone did not prevent source and proof
intrusion. Publisher-specific export, visual declarations and archive hash
refresh transferred publication maintenance into the source product.

## Goals and Non-goals

Remove every drawing-only input, exporter, package, test and runtime dependency
from ETHOS. Preserve product-native documentation, declared producer relations,
archive link relocation, installation and release acceptance. This change does
not redesign the renderer or require ETHOS to adopt another diagram contract.

## Decisions

- The independent architecture-publications repository owns editorial data and
  artwork. It reads pinned Git objects without writing or running drawing code
  in ETHOS. Publisher remains a generic dependency of that editorial repository.
- Preserve unique inputs by byte comparison before deletion; preserve source
  history through Git and accepted PNG/HTML without regeneration.
- Remove terminal-specific binding and assurance code from the projection owner
  and OpenSpec archive adapter. Keep generic projection and relocation behavior.
- Replace the misleading npm drawing test with actual existing launcher and
  package acceptance. Do not remove its native quality gate or coverage floor.

## Migration and Recovery

Copy the exact selected editorial inputs and required artwork sources to the
external owner's admitted Lane. Record Git revision and member digests there,
then remove the source implementation and every caller in one bounded batch.
Run focused archive, producer, schema, package and source quality checks.
A failed check holds landing, not the independent external work. Git retains
the preimage; accepted user deliveries remain unchanged.

## Acceptance and Closeout

No live terminal-export or Publisher dependency remains in ETHOS code,
configuration, tests or current documentation. Generic archive and producer
journeys pass, and external input generation leaves source Git state unchanged.
The source owner lands the exact reviewed contribution through native ETHOS;
local tests and handoff do not establish accepted-root or remote convergence.
