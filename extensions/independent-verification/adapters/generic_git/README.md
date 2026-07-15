# Generic Git pre-receive adapter

This optional reference adapter protects only provider-configured Git refs. It
is **off by default**: an uninstalled hook, or `mode = "disabled"`, accepts
every update and changes no ETHOS lifecycle command or ordinary adoption path.

## Provider control plane

The provider owns one protected TOML file outside every governed repository.
It must be neither group- nor world-writable. The hook reads this file only;
it never reads configuration from the pushed tree. Enabling the adapter needs a
provider's receipt store and protected SSH signer list, but it never makes an
account, key, daemon, network service, or `yheng-agent-ethos` required for an
adopter that leaves it disabled.

```toml
mode = "required"
bare_repository = "/srv/git/example.git"
remote = "ssh://git.example.invalid/example.git"
receipt_store = "/srv/ethos/receipts"
allowed_signers = "/etc/ethos/allowed_signers"
namespace = "ethos-independent-verification"
implementation_digest = "<64-lowercase-hex>"
proof_floor_id = "ethos:promotion-required-gates:v1"
proof_floor_digest = "<64-lowercase-hex>"
policy_digest = "<64-lowercase-hex>"
action = "publish"
freshness_seconds = 600
protected_refs = ["refs/heads/main"]
```

The shown digests are placeholders, not valid values. The bare repository,
receipt directory, and signer list must already exist before `mode =
"required"` is used. If the provider has a global `core.hooksPath`, configure
that bare repository's `core.hooksPath` explicitly to its provider-owned hook
directory; otherwise Git will not consult the default `<bare>/hooks` location.

Install the provider's standard pre-receive wrapper so it executes only the
fixed adapter and config path:

```sh
exec /opt/ethos/extensions/independent-verification/adapters/generic_git/pre_receive.py \
  --config /etc/ethos/generic-pre-receive.toml
```

## Enforcement contract

For each configured protected, non-deletion ref, the adapter resolves the
proposed tree with `/usr/bin/git` and accepts only a provider-store receipt
named `<commit>-<action>.json`. The receipt must pass canonical payload-digest
and SSH-signature verification and bind exactly to the configured remote,
proposed commit/tree, action, proof-floor ID/digest, policy digest, and
implementation digest. The valid interval may not exceed `freshness_seconds`.

Protected deletion, missing receipt, malformed data, digest mismatch, stale
receipt, binding mismatch, or signature failure rejects the update with a
stable `ethos-generic-pre-receive:<reason>` error. Unprotected refs require no
receipt. The adapter invokes no client-supplied command and makes no network
call; it does not claim semantic correctness or authority.
