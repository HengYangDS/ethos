# Managed-hook deployment bootstrap closeout

## Why

A protected `accepted_ff` closeout can promote a revision of
`.githooks/reference-transaction`. Before `dev` advances, Git necessarily
executes the incumbent accepted-checkout shell hook. That incumbent hook can
validate the accepted-ref member through the candidate semantic runner, but it
cannot use the new shell routing for the companion `main` member. A one-shot
atomic dual-ref transaction therefore blocks before the new hook reaches the
accepted checkout.

## What Changes

- Keep the ordinary `accepted_ff` closeout atomic when the tracked
  `reference-transaction` hook is unchanged.
- For the narrow case where the candidate changes that hook, use two official,
  intent-bound ref transactions: promote `dev` through the incumbent hook,
  synchronize the accepted checkout to the candidate tree, then promote the
  release mirror through the now-promoted hook.
- Treat an interruption after the first transaction as explicit
  `release_mirror_bootstrap_incomplete` residue, not as completed closeout.
- Add a real armed-hook regression in which incumbent shell routing rejects the
  release member while the promoted candidate hook admits it.
- Cover a failed second leg as explicit incomplete mirror residue.

## Capabilities

- `adapters`: subject=managed-hook-deployment-bootstrap-closeout; reuse=extend; change=modify; facet:lifecycle=closeout,validation; facet:surface=hook,cli,test,openspec,evidence; facet:authority=source,test,openspec,evidence

## Out Of Scope

- No direct ref move, hook disablement, environment bypass, or temporary
  `core.hooksPath` override.
- No remote GitHub/GitLab mutation, submit reconciliation, or foreign Work Lane
  mutation.
- No general weakening of atomic release-mirror closeout.
