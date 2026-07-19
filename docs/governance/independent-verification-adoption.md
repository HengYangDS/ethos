---
subject: ethos:independent-verification-adoption
role: policy
state: canonical
relations:
  canonical_for: optional independent proof re-execution adoption
---

# Optional Independent Verification Adoption

Status: canonical.

Purpose: define the optional, provider-neutral adoption boundary for independent
proof re-execution.

See also: [DR-0006](../decisions/accepted/DR-0006-proof-trust-boundary.md),
[Adoption Profiles](../architecture/adoption-profiles.md), and
[Capability Parity Ledger](capability-parity-ledger.md).

ETHOS remains local-first by default. Independent proof re-execution is an
optional adapter for an adopter that needs a separate trust identity for a
specific transition; it is neither a product authority nor an adoption
prerequisite.

## Adopter Policy

An adopter may omit this table entirely. The default is `disabled` and `publish`
continues to report `local_readiness` only:

```toml
# .ethos/profile.toml
[independent_verification.actions.publish]
mode = "optional" # or "required"
```

`optional` accepts an absent receipt and reports `local_readiness`; a supplied
receipt must still validate. `required` blocks **only** `ethos publish` until a
valid receipt exists. It does not add a provider, account, path, key, anchor,
or network requirement to `status`, `plan`, `prove`, `land`, or another action.

The product ships disabled, optional, and required external-adopter fixtures
under `tests/fixtures/independent-verification-adopters/`. They are policy
fixtures, not a product self-shadow and not external parity evidence.

## Provider-Local Control Plane

The receipt path is supplied at invocation through
`ETHOS_INDEPENDENT_VERIFICATION_RECEIPT`; it is accepted only when it lies in
the protected receipt store declared by a system provider configuration. ETHOS
searches these provider-local paths, never an adopter checkout:

```text
/Library/Application Support/ETHOS/independent-verification.toml
/etc/ethos/independent-verification.toml
```

The configuration, its parent, the receipt store, and the allowed-signers file
must be owned by an identity other than the invoking agent and must not be
group- or world-writable. A minimal configuration is:

```toml
[receipt_store]
root = "/var/db/ethos/independent-verification/receipts"

[signature]
allowed_signers = "/var/db/ethos/independent-verification/allowed-signers"
namespace = "ethos-independent-verification"
implementation_digest = "<sha256 of the pinned out-of-tree ETHOS runtime>"
```

The public anchor, receipt-store path, verifier account, private signing key,
and runtime digest stay in that provider-local control plane. Do not put them
in `.ethos/profile.toml`, an OpenSpec record, evidence claim, or an adopter
repository. A receipt binds an exact remote, commit, tree, action, proof floor,
gate-policy digest, and verifier-runtime digest. It proves only that bounded
floor was re-executed by the configured provider; it does not prove semantic
correctness or mint authority.

## Provider Implementation Boundary

ETHOS ships the provider-neutral request, receipt, signature-verification, and
admission contract. It does not ship a verifier executable, daemon, scheduler,
or Git hook. Operators that opt into independent re-execution supply and own an
out-of-tree implementation under an identity the governed agent cannot modify.

That implementation must use a pinned out-of-tree ETHOS runtime, re-execute the
declared proof floor against the exact remote, commit, and tree, protect its
signing key and receipt store, and emit the exact signed receipt consumed by the
admission boundary. Generated requests intentionally leave the implementation
digest blank; the protected provider configuration supplies it. ETHOS does not
create accounts, services, schedules, keys, hooks, or system configuration.

Use a local immutable mirror when offline operation is required. A hosted forge
or a separately managed local service may implement the same receipt contract;
both remain provider deployments rather than product-distributed examples.

## External-Adopter Readiness

For an actual external repository, create a clean checkout and run:

```bash
ethos adopt --root <adopter> --profile generic --json
ethos status --root <adopter> --json
ethos prove --root <adopter> --json
ethos report --root <adopter> --json
```

Then set the desired policy mode in that adopter, run its provider-owned
re-execution path when opted in, and retain its signed receipt outside the
repository. Prove command and documentation parity with:

```bash
ethos parity shadow --adopter <adopter-id> --root <product> --target <adopter> \
  --execute --write-evidence --json
```

The generic product self-shadow is useful for product regression detection, but
it is not external-adopter parity: it does not supply a distinct Git subject,
profile, provider configuration, or adopter-owned evidence root.
