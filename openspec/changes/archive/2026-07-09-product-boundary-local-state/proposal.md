# Product Boundary Local State

## Why

The product-boundary gate must reject local workstation paths in active product
truth while preserving the boundary that ignored `.ethos/state/**` files are
host-local runtime projections, not product surfaces. Candidate proof carry can
write `.ethos/state/proof/<head>.json` files containing absolute local paths;
scanning those ignored files as product truth turns local proof state into a
false product-boundary gap.

## What changes

- Keep `.ethos/state/**` outside active product-boundary text scanning.
- Preserve scanning for active `.ethos` configuration such as `.ethos/workspace.toml`.
- Add a regression test proving local proof records are not product surfaces.

## Boundary

This does not allow local workstation paths in tracked product docs, configs,
source, tests, release metadata, OpenSpec specs, or evidence claims. It only
keeps ignored host-local proof state from masquerading as product truth.
