---
subject: ethos:guide:independent-verification
role: how-to
state: active
relations:
  canonical_for: optional independent proof re-execution setup
---

# Independent Verification

Status: active.

Purpose: set up optional re-execution of proof under an independent trust identity for one governed repository.

See also: [ETHOS source repository-governance specification](../../openspec/specs/repository-governance/spec.md "source-only"), whose independent-verification requirements own the behavior, and [Command Plane](../reference/command-plane.md).

ETHOS stays local-first. Independent verification is an operator-deployed provider outside repository write authority; it changes no command semantics, and a local result never claims independent identity.

## 1. Bind And Prove

Bind the repository and prove its exact head:

```bash
ethos adopt --root <repo> --json
ethos prove --root <repo> --execute --full --expect-head <HEAD> --json
```

## 2. Declare The Policy

In `.ethos/profile.toml`, `[independent_verification] mode` sets the mode for every action: `disabled` (the default), `optional` or `required`. Publication alone can take its own mode:

```toml
[independent_verification.actions.publish]
mode = "required"
```

Control replacement reads the top-level mode.

## 3. Install The Provider Configuration

The operator, not the repository, installs one host file: `/Library/Application Support/ETHOS/independent-verification.toml` on macOS or `/etc/ethos/independent-verification.toml` on Linux. It names the receipt store and the public verification inputs:

```toml
[receipt_store]
root = "/absolute/path/to/receipts"

[signature]
allowed_signers = "/absolute/path/to/allowed_signers"
namespace = "<signature namespace>"
implementation_digest = "<sha256 of the verifier implementation>"
issuer = "<issuer>"
key_id = "<key id>"
```

Every path component must be protected from the invoking user. The file holds only public verification inputs; signing keys stay with the provider. A missing, unreadable or unprotected configuration makes ETHOS ask for operator repair before it asks for a receipt.

## 4. Obtain A Receipt

The provider re-executes the proof and writes a signed receipt into its protected store. The receipt follows `system/schemas/kernel/independent-verification-receipt.schema.json` and binds the exact repository, commit, tree, action, proof floor, policy, implementation and issuer.

## 5. Present It And Re-Observe

Pass the receipt's actual path to the effect that requires it:

- closeout: `ethos land --closeout … --independent-verification-receipt <path>`;
- publication: `ETHOS_INDEPENDENT_VERIFICATION_RECEIPT=<path> ethos publish …`.

Then re-run the reader. Only a passing current decision permits the effect. Status, proof, package tests and local signatures never create a receipt.
