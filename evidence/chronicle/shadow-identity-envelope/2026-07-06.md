---
subject: evidence:shadow-identity-envelope
role: delivery-evidence
state: active
relations:
  canonical_for: shadow parity identity envelope validation
---

# Shadow Identity Envelope Evidence

Date: 2026-07-06

## Claim

ETHOS shadow parity reports and tracked parity evidence now carry an identity
envelope before adopter retirement checks consume semantic diff results.

The identity envelope binds:

- target root;
- target HEAD;
- product HEAD;
- changed paths;
- compared product command identities;
- compared embedded backend command identities;
- evidence input digests.

## Validation

Executed in `/private/tmp/ethos-shadow-identity-envelope`:

```bash
uv run --group dev pytest tests/unit/product/test_parity.py tests/unit/product/test_parity_generic.py tests/unit/governance/test_validation_gates.py tests/unit/cli/test_command_registry.py -q
.config/ci/scripts/run-python-lint.sh
.config/ci/scripts/run-config-lint.sh
npx --yes @fission-ai/openspec@1.5.0 validate --all --strict
uv run --package ethos ethos openspec --lifecycle --json
```

Observed results:

- focused parity / schema / registry tests: `98 passed`;
- Python lint owner script: passed;
- config lint owner script: passed;
- official OpenSpec validation: `10 passed, 0 failed`;
- ETHOS OpenSpec lifecycle: `ok=true`, `required_gaps=[]`.

## Boundary

This is not adopter retirement. It only creates the evidence identity carrier.
Retirement still requires a domain false-negative suite, rollback-window evidence,
and same-state shadow evidence for the adopter being retired.

Status: see front matter.

Purpose: record validation evidence for the shadow parity identity envelope.

See also: [Capability Parity Ledger](../docs/governance/capability-parity-ledger.md),
[Adopter Boundary And Retirement](../docs/governance/adopter-boundary-and-retirement.md),
and [OpenSpec Change](../openspec/changes/archive/2026-07-06-shadow-identity-envelope/proposal.md).
