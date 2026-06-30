# ETHOS Kernel

## Purpose

ETHOS SHALL model repository operation through Constitution, Subject,
Commitment, Change, Evidence, Chronicle, and Evolution.

## Requirements

- ETHOS SHALL expose one public command plane rooted at `ethos`.
- ETHOS SHALL keep external standards as protocols or adapters.
- ETHOS SHALL keep local runtime state ignored and non-authoritative.
- ETHOS SHALL serialize action graphs deterministically, including validation
  gaps for invalid graphs.
- ETHOS SHALL emit stable JSON result envelopes with `ok`, `summary`,
  `diagnostics`, `required_gaps`, `next_actions`, and `data`.
- ETHOS SHALL project proof-readiness into evidence sets and provenance
  envelopes without treating local state as durable evidence.
- ETHOS SHALL keep assistant, MCP, ACP, hosted CI, and workflow runtimes as thin
  projections over repository truth.
- ETHOS SHALL gate apply-mode land and publish readiness on explicit
  authorization plus expected HEAD.
- ETHOS SHALL validate tracked JSON Schemas before treating command output as
  automation-ready.
- ETHOS SHALL run proof gates through the action graph and bind selected gate
  runs into evidence.
- ETHOS SHALL expose release, commit signature, schema, gate, and command
  example readiness through `ethos quality`.
- ETHOS SHALL keep adoption profiles and MCP server integration as adapters
  outside the pure kernel.
