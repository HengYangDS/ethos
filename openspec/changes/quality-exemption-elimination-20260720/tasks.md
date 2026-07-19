## 1. Contract and inventory

- [x] 1.1 Record the live exception inventory and create the OpenSpec contract.
- [ ] 1.2 Add regression coverage that rejects every retired Ruff exception shape (UTC default-clock contract added; carrier rejection remains).

## 2. Direct enforcement

- [ ] 2.1 Refactor tracked Python carriers until the full selected Ruff rule set is clean (DTZ011 eliminated; remaining rules stay explicit).
- [ ] 2.2 Delete global/path ignores, source suppressions, the ratchet file, and the ratchet runner.
- [ ] 2.3 Converge gate registry, tool registry, owner script, documentation, and tests on direct enforcement.
- [x] 2.4 Route the type adapter through the checkout-local runtime bootstrap so an unmaterialized Work Lane cannot read another environment, emit false missing-dependency diagnostics, or inherit a misleading active-venv warning.

## 3. Evidence and closeout

- [ ] 3.1 Run focused quality contracts and full owner scripts.
- [ ] 3.2 Refresh parity evidence, execute head-bound proof, land through candidate, close accepted root, and retire this owned lane.
