---
subject: evidence:product-migration-closure
role: evidence
state: active
relations:
  supports: ethos-product-migration-closure
---

# Product Migration Closure Evidence

This evidence records the ETHOS product migration closure batch in
`work/product-migration-closure`.

## Scope

- Retired active product migration-host packages from `packages/`.
- Moved npm launcher packaging to `distributions/npm`.
- Kept the target Python package ontology to:
  `ethos-core`, `ethos-contracts`, `ethos-repository`, `ethos-assistants`,
  `ethos-adapters`, `ethos`, and `ethos-test`.
- Removed the reverse dependency from `ethos-repository` to `ethos-adapters`;
  deep provider checks are now composed by the CLI with injected adapters.
- Added command-registry checks for retired family-style command prefixes such
  as `ethos governance` and `ethos workspace`.
- Moved canonical OpenSpec specs to the target MECE families and archived all
  completed changes with the official OpenSpec CLI.
- Preserved alphasim-dmgr as adopter oracle and fallback by using tracked
  parity evidence rather than deleting adopter-embedded ETHOS.
- Closed final review gaps where active `.ethos/workspace.toml` and active
  claims could still carry retired migration-host family names after packages
  had been physically migrated.
- Added self-governance checks so `ethos quality package-ontology`, `ethos
  quality claims`, and `ethos self audit` detect retired product-family
  leakage in active workspace config and active claims.

## Worktree Safety

This batch stayed in the isolated Work Lane:

```text
work/product-migration-closure
```

`ethos status --json` reported a foreign Work Lane,
`work/neutral-state-semantics`, through git worktree metadata. That Work Lane
was not entered, modified, cleaned, or retired.

Remote publication was intentionally out of scope.

## Verification

Fresh verification run during this batch:

```bash
uv run --group dev pytest -q tests/unit tests/architecture
uv run --group dev ruff check .
openspec validate --all --strict --json
uv build --all-packages
npm ci --ignore-scripts
npm run ethos -- --version
npm run test:npm
uv run --package ethos ethos self audit --mode deep --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos quality command-registry --json
uv run --package ethos ethos quality package-ontology --json
uv run --package ethos ethos quality command-examples --json
uv run --package ethos ethos report --json
uv run --package ethos ethos status --json
uv run --package ethos ethos plan --changed --json
uv run --package ethos ethos parity gaps --json
uv run --package ethos ethos prove --execute --gate self-audit --json
uv run --package ethos ethos prove --full --execute --json
```

Observed results:

- Unit and architecture tests: 245 passed in 42.98s after review hardening.
- Focused review-hardening tests covered active workspace config, active claim
  retired-family detection, product package ontology reporting, and adoption
  scaffold subject convergence.
- Ruff: all checks passed.
- OpenSpec strict validation: 8 specs passed, 0 changes active, 0 failures.
- Python build: all 7 Python packages built wheel and sdist locally.
- npm: `npm ci --ignore-scripts` completed with 0 vulnerabilities;
  `npm run ethos -- --version` returned `0.1.0a1`; `npm run test:npm`
  dry-run packed `@agentic-workflow/ethos`.
- Deep self-audit: `ok=true`, required gaps empty, migration status complete.
- Claims: active claim evidence SHA-256 bindings matched.
- Command registry: no retired public root or retired family-style command
  prefix mentions in current docs.
- Package ontology: 7 target packages, 0 migration hosts,
  `migration_status=complete`, `distributions/npm` migrated, workspace config
  lists only the target 7 packages.
- Product report: score 15/15, product gap count 0, parity pending count 0.
- Parity gaps: `gap_count=0` for generic tracked shadow evidence.
- Full proof: 8 gates passed with required gaps empty after the product
  migration closure changes were committed and review gaps were addressed.
