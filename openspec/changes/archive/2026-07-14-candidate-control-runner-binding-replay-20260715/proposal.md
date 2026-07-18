# Candidate Control-Runner Binding Replay

## Why

Accepted-root ref admission is deliberately fail-closed, yet its hook runs before
accepted source reaches the candidate commit being promoted. A candidate change
to admission semantics can therefore be judged by accepted-old imports rather
than by the exact tree whose proof is offered. The resulting failure is a
provenance error: a valid candidate closeout is evaluated through the wrong
control implementation.

## What Changes

- Bind accepted-ref semantic admission to the clean linked checkout of the
  configured candidate branch at the exact proposed candidate HEAD.
- Retain the accepted checkout as the shell-hook, CAS, and protected-ref
  boundary; a missing, dirty, detached, stale, or unbindable candidate runner
  fails closed.
- Preserve the one-shot closeout intent, candidate proof, transition, and
  external control-replacement boundaries; a raw ref move to the same proven
  candidate HEAD remains denied.
- Add an armed-hook regression in which accepted-old policy fails while the
  candidate policy admits the sanctioned closeout.

## Capabilities

- `adapters`: subject=accepted-ref-candidate-control-runner; reuse=extend;
  change=modify; facet:lifecycle=runtime,validation; facet:surface=hooks,cli,test;
  facet:authority=source,test,openspec,evidence
- `repository-governance`: subject=accepted-ref-candidate-control-runner;
  reuse=extend; change=modify; facet:lifecycle=runtime,validation;
  facet:surface=hooks,cli,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- No candidate tree self-authorizes promotion: independent control-replacement
  receipt policy remains unchanged.
- No waiver, accepted-old fallback, or raw-ref bypass is introduced.
- No foreign Work Lane, candidate checkout, or accepted checkout is mutated
  directly by this change.
- No remote push or hosted-CI success is implied by local closeout admission.
