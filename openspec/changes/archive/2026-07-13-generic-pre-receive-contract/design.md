## Context

The existing independent-verification receipt already binds an independently
re-executed proof floor to a remote, commit, tree, action, floor digest, policy
digest, provider implementation digest, issuer, and signature. Generic Git has
a pre-receive hook point that sees proposed ref updates before a server accepts
them. The adapter must consume that contract without making a server or an
independent verifier mandatory for all ETHOS adopters.

## Goals / Non-Goals

**Goals:** provide a provider-local, default-off generic Git hook for configured
refs; reject missing, stale, unsigned, malformed, or mismatched receipts; and
keep the adapter physically colocated with independent-verification reference
sources.

**Non-Goals:** create users, keys, trust anchors, receipts, schedules, daemons,
network calls, generic subprocess execution, product commands, or a required
adopter dependency. The hook verifies a bounded re-execution receipt; it does
not prove semantic correctness or authority.

## Decisions

### Provider-local configuration is the control plane

The hook reads one provider-owned, protected TOML configuration outside a
governed repository. It declares `disabled` or `required` mode, the exact bare
Git directory and remote identity, protected refs, receipt store, allowed
signers, SSH namespace, expected proof-floor ID/digest, expected policy digest,
and freshness window. `disabled` accepts every update; installing no hook is
equivalent to disabled. Repository profile files cannot provide these values.

### Receipt lookup and comparison are exact

For every protected non-deletion update, the hook resolves the proposed tree
from the configured bare repository and loads only the provider-store receipt
named by the proposed commit and action. It validates canonical payload digest,
SSH signature, result and validity interval, then requires exact equality for
remote, commit, tree, action, proof-floor ID/digest, policy digest, and provider
implementation digest. Protected deletion has no tree-bound receipt and is
rejected. Unprotected refs are passed through.

### Git is the only execution boundary

The hook reads standard pre-receive stdin and invokes only a fixed absolute Git
binary to resolve the proposed tree. It never runs a command received from the
client, fetches the network, or evaluates a pushed configuration. GitHub and
GitLab can project this contract but may not duplicate the receipt verifier.

### Optionality and physical placement are structural

The adapter lives at
`extensions/independent-verification/adapters/generic_git/`, alongside its
manifest, documentation, and focused tests. The extension is default-off; no
ordinary ETHOS status, plan, prove, land, or local publication path depends on
it or on `yheng-agent-ethos`.

### Source-budget admission precedes executable implementation

This checkout has no free `python_other` allowance. A narrow, expiry-bound debt
record must be admitted through its owning configuration lane before the adapter
source and tests are written; it must name the carrier, replacement/deletion
wave, category allowance, and focused proof. This prevents a server adapter
from silently bypassing the product's hard source budget.

## Risks / Trade-offs

The hook adds protection only where a provider installs and enables it; direct
server administration can still remove it. Exact policy pinning requires a
provider to update its protected configuration when a new policy is deliberately
promoted. That operational cost is intentional: it avoids treating a pushed
tree as its own enforcement authority.
