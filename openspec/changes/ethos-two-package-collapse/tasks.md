## 1. Pre-flight

- [x] Green baseline recorded (ruff / import-linter / ty / code-size / pytest).
- [x] Work Lane started with lease; OpenSpec carrier authored.

## 2. Merge into ethos-core (pure leaves)

- [ ] 2.1 ethos-quality -> ethos_core.quality (safest pilot: fewest sites, 0 intra-coupling, 0 ratchet exceptions).
- [ ] 2.2 ethos-contracts -> ethos_core.contracts (lift the tomllib-in-core boundary ban first).

## 3. Merge into ethos (product runtime)

- [ ] 3.1 ethos-assistants -> ethos.assistants.
- [ ] 3.2 ethos-adapters -> ethos.adapters (co-locate with existing ethos/adapters/).
- [ ] 3.3 ethos-repository -> ethos.repository (add jsonschema dep to ethos).
- [ ] 3.4 ethos-test -> ethos.testing.

## 4. Cutover

- [ ] 4.1 Flip TARGET_PACKAGES SSOT + .ethos/workspace.toml to 2 packages; collapse
      import-linter to a 2-layer contract; collapse ty policy; delete the 6 empty
      package dirs.
- [ ] 4.2 Full gate suite green; `ethos prove --execute`; land to candidate; retire lane.
