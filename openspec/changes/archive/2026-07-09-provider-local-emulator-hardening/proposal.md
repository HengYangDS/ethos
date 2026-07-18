# Provider Local Emulator Hardening

## Problem

ETHOS already exposes GitHub and GitLab local emulator wrappers, but the evidence
envelope needs stronger trust boundaries before emulator output can participate in
provider-profile proof. Local emulators can omit untracked files during provider
materialization, and an emulator run must show that the Git head remained stable
from start to finish.

## Change

Harden local provider emulator evidence for both GitHub and GitLab. The wrapper
payloads now include start/end Git summaries, changed-scope previews, head
stability, template/projection/config file facts, and an explicit refusal for
normal emulator runs when untracked files are present unless a non-proof override
is supplied.

## Capabilities

- `repository-governance`: subject=local-provider-emulator-evidence; reuse=extend; change=modify; facet:lifecycle=evidence; facet:surface=provider,ci,script,test; facet:authority=source,test,docs,openspec

## Out Of Scope

- No hosted GitHub or GitLab success claim.
- No remote publication claim.
- No replacement of local owner gates or head-bound ETHOS proof.
- No requirement that adopters use GitHub or GitLab as product substrate.
