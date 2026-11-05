# Tasks

## 1. Verified declaration

- [ ] 1.1 Specify the declaration with failing tests. Done when unit tests fail for three cases:
      Node declared in both inventories when the catalog misses `node.exe` and its digest matches
      the locked supply; a digest mismatch refusing with
      `release_inventory_component_unverified:node`; and a cataloged Node adding nothing.
- [ ] 1.2 Declare locked components that the catalog misses in `tools/ci/release_supply_chain.py`.
      Done when those tests and the existing inventory tests pass, and the supply-chain evidence
      lists the declared components.

## 2. Hosted acceptance

- [ ] 2.1 Catalog a Windows archive with the declaration. Done when a hosted Windows run on Python
      3.14 catalogs its kept archive with Node declared and the inventory checks passing.
