# Proposal

## Why

Official archive can leave authored documents linked to the removed active Change. The
archive is attested, but exact-path admission then blocks the document repair needed to
restore valid navigation. A managed adopter has reproduced this through its normal CLI.

## What Changes

- Derive a bounded repair path from the attested archive move and the exact current Git
  tree, using the existing Markdown reference parser.
- Admit only tracked Markdown consumers whose parsed destination still names that move;
  preserve authored control of surrounding prose and existing patch/hook checks.
- Reject unrelated files, code examples, missing destinations and missing archive
  authority. Add no durable repair carrier or parallel lifecycle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: permit exact authored reference repair after a verified
  OpenSpec archive without reopening or replaying the completed Change.

## Impact

The existing archive reference adapter, OpenSpec material-scope resolver, and public
prewrite/hook tests change. No new runtime dependency or adopter-specific rule is added.
