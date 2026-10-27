# System Contracts

Source-owned declarations and interpretation constraints live here. Their meaning
is bounded by the [product design contract](../docs/governance/product-design-contract.md),
accepted [ETHOS source OpenSpec intent](../openspec/ "source-only"), and the
[rule contract](../rules/README.md).
This directory is not another product definition or runtime state store.

## Definitions And Boundaries

| Carrier                      | Carries                                                                                                     | Excludes                                                        |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `system/`                    | Foundational interpretation constraints, machine-readable declarations, schemas, and projection definitions | Product deployment, mutable state, or a second intent authority |
| `src/ethos/resources/`       | Authored package-specific static inputs without another canonical source owner                              | User data, adopter policy, caches, or ETHOS implementation      |
| Installed `ethos/resources/` | The version-matched, selected read-only package closure                                                     | New authority over its source contracts or permission to act    |
| `assets/`                    | Visual and media source material                                                                            | Governance contracts or automatically shipped runtime inputs    |
| `.config/`                   | Tool-native configuration                                                                                   | Business scripts or another implementation layer                |
| `build/`                     | Bounded, reproducible derived output                                                                        | Accepted meaning or indefinite evidence custody                 |

Runtime state, leases, caches and effect receipts belong to their declared native
state/evidence stores, never the immutable resource closure. A path is a carrier:
classify what it holds before treating it as source, projection, supply or state.

A source owner is the single maintained definition consumed by its dependants;
a carrier is its physical location. Neither a directory name nor inclusion in a
package creates authority. Product meaning, accepted Change intent, executable
obligations, guidance, and observed evidence retain their distinct owners.

A product resource is a non-code input read without mutation by its installed
consumer. Read-only describes installed use, not the source author's ability to
revise it. Schemas, guidance, native supply declarations, locks and immutable
build identity are resources with different roles: a schema defines a contract;
a lock describes supply; identity binds a build; guidance supplies a method.
Prepared production modules are executable supply, even when a build owner
places them inside the installed resource closure. That physical containment
does not make them declarative resources or policy. Neither shipping a resource
nor calling it a contract grants execution authority.

Classify an input by its meaning, source owner, and actual consumer before moving
or including it. A required schema stays in its canonical `system/schemas/`
owner and is selected for publication; it is not relocated merely because the
installed product needs it. `resources/` is neither a replacement for `system/`
nor a catch-all for the repository. Select required product inputs, not all files.

## Owners And Navigation

| Concern                                 | Source owner                                                                                    |
| --------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Foundational interpretation             | [Axioms](axioms.md)                                                                             |
| Gate executors and evidence obligations | [Gate declaration](gates.toml)                                                                  |
| Evidence relationships                  | [Source evidence boundaries](evidence-boundaries.toml "source-only")                            |
| Routing and public surfaces             | [Source routing](routing.toml "source-only") and [source surfaces](surfaces.toml "source-only") |
| Native carrier formats                  | [Source formats](formats.toml "source-only")                                                    |
| Schemas and their local references      | `schemas/`; [contract schemas](schemas/contracts/README.md)                                     |
| Publication projections                 | [Source projection owners](projections/README.md "source-only")                                 |

## Source And Installed Resources

Canonical schemas stay in `system/schemas/`; canonical rules and documentation
stay in their existing `rules/` and `docs/` owners. The native Hatch declaration
in [pyproject.toml](../pyproject.toml) selects the shipped closure and preserves
source-relative names beneath `ethos/resources/`: for example, `system/schemas/`
becomes `ethos/resources/system/schemas/`. Source-only package inputs already
under `src/ethos/resources/` retain their suffix. It does not maintain a checked-in
mirror; storage location neither promotes a projection nor changes its source owner.
Prepared modules and generated build identity have explicit build owners rather
than becoming authored `system/` declarations.

The [source resource locator](../src/ethos/repository/release/resources.py "source-only") selects the
loaded product, never the caller's current directory or an adopter lookalike.
A source runner reads its own canonical source; an installed runner reads its
version-matched package inputs. Missing required input is an error, not a reason
to fall back to another product generation. Locators do not grant permission.

A native source build validates complete prepared Node supply. Python lock export
and installation consume their own declared inputs; the presence of a Node lock
beside them does not add a full npm-install prerequisite.

The real source-distribution-to-wheel check verifies every selected source file
against package bytes, together with exact build identity. Publication, installed
consumer behavior, upgrade, recovery, and exit are separate acceptance claims.
This layout migration does not by itself establish those claims.

Required installed navigation resolves within the selected resources. Links
labelled `source-only` explain ETHOS development and do not enlarge package
selection. They are not required installed inputs, adopter intent or permission.
