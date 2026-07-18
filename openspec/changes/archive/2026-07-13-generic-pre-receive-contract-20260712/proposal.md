## Why

ETHOS has a local admission surface and an optional independent verifier, but a
cooperating local hook can be bypassed by a direct Git ref update. A generic Git
server needs an opt-in, provider-local pre-receive adapter that consumes the
same exact independent-verification receipt without turning an account, key,
daemon, network service, or `yheng-agent-ethos` into an adoption prerequisite.

## What Changes

- Add a default-off `generic_git` adapter under the existing
  `independent-verification` extension bundle; no root-level reference-adapter
  directory or product command is introduced.
- Let a provider-owned pre-receive configuration select protected refs and
  require one signed receipt bound to the proposed commit, tree, action, proof
  floor, and gate-policy digest.
- Keep GitHub and GitLab as thin projections over this receipt contract rather
  than adding a second governance kernel.
- Record a bounded source-budget carrier before executable adapter code is
  admitted; the global budget remains a hard cap.

## Capabilities

- `adapters`: subject=generic-git-pre-receive-receipt-adapter; reuse=extend;
  change=modify; facet:lifecycle=validation,evidence,archive;
  facet:surface=adapter,configuration,docs,test,openspec,evidence;
  facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Requiring an OS identity, account, key, receipt store, daemon, scheduler,
  network service, hosted forge, or the `yheng-agent-ethos` user for ordinary
  adopters.
- Running arbitrary commands, deriving policy from an untrusted pushed tree,
  creating a new product lifecycle command, or claiming semantic correctness.
- Replacing GitHub or GitLab adapters, hosting a forge, or publishing remotely.

## Impact

The future implementation is confined to the independent-verification
extension, its tests, docs, and declared source-budget carrier. It consumes the
existing receipt contract and does not change the product's local-first default.
