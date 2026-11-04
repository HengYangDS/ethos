# Tasks

## 1. Inventory owner

- [ ] 1.1 Retarget `tools/ci/release_supply_chain.py` and its policy to the archive that the
      install smoke keeps, with one Syft run that writes both inventories. Done when tests with a
      fake Syft show three things: the run reads `file:<archive>` under the published name and
      the explicit configuration; inherited `SYFT_` variables are removed; a foreign or empty
      inventory refuses.
- [ ] 1.2 Check completeness against the owners. Done when tests show that a missing Go module,
      `uv` crate, Node or Python distribution is each named, and that a complete inventory
      passes.
- [ ] 1.3 Run the gate after `local-install-smoke` in proofs. Done when the gate declaration
      depends on it and reads its locks, and the documentation describes the new subject.

## 2. Publication

- [ ] 2.1 Admit inventories in `release_assets.py`. Done when tests show five things:
  - matching inventories are published and summed;
  - a missing, garbled or oversized inventory refuses;
  - a foreign digest or name refuses;
  - a one-package SBOM refuses;
  - a Windows host without inventories is left out.
- [ ] 2.2 Run the owner in every release leg, upload the inventories with the archive, and add
      them to the provenance subjects. Done when the GitHub projection is regenerated and
      `lane project --check` reports it conforming.

## 3. Specification and notes

- [ ] 3.1 Add the `distribution` requirement. Done when strict validation and the cumulative
      archive simulation pass.
- [ ] 3.2 Name the change in the Unreleased notes. Done when the changelog validates.
