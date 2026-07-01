## 1. Product Topology

- [x] 1.1 Move active product code into target MECE packages.
- [x] 1.2 Move npm launcher packaging to `distributions/npm`.
- [x] 1.3 Remove migration-host packages from the Python workspace.
- [x] 1.4 Refresh uv and npm locks.

## 2. Dependency Boundaries

- [x] 2.1 Keep package roots free of re-export shells.
- [x] 2.2 Keep `ethos-repository` independent of provider adapters.
- [x] 2.3 Keep adapters from importing the public CLI surface.
- [x] 2.4 Keep product code free of adopter-private implementation names.

## 3. Governance Records

- [x] 3.1 Move canonical OpenSpec specs to target MECE families.
- [x] 3.2 Move active OpenSpec deltas off retired families.
- [x] 3.3 Update active claim scopes to target packages and distributions.
- [x] 3.4 Track generic shadow parity evidence.

## 4. Verification

- [x] 4.1 Run focused architecture and unit tests.
- [x] 4.2 Run broad unit and architecture tests.
- [x] 4.3 Run Ruff, OpenSpec validation, Python build, npm install, npm
      launcher smoke, and npm pack dry-run.
- [x] 4.4 Run ETHOS deep audit, parity gaps, report, and execution proof.
