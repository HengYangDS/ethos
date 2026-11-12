# Proposal

## Why

beta.9 is a fix release. A Work Lane handed off after its proof could not land on its new holder's
proof: the repository transition refused `contradiction` between the two holders' proofs of one
HEAD, so a governed repository's handoff blocked its landing (reported by an adopter's owner on
2026-11-12). The release also carries OpenSpec 2.0.0, which the owner asked for in ETHOS and every
governed repository on 2026-11-12, and what landed after beta.8: the documentation registry's
tutorial role, landing 1 of the history rebuild (the census and readiness), and the supply move.

## What Changes

- `VERSION` moves to `0.2.0-beta.9`.
- The `[Unreleased]` entry becomes the `0.2.0-beta.9` entry, completed from the landed Changes and
  the release build's audit. It names the upgrade paths its journey qualifies, the journeys this
  beta does not qualify, every advisory the audit reports, and the known open defects a user can
  meet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md` and `VERSION`.
