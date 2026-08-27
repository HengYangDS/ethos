# Proposal: Remove the false local proposal lane

## Problem

`proposal/*` is a remote review ref, but branch-role classification also models it as a local authoring lane. That duplicates authority and blocks the intended `work/* -> prove -> proposal/*` flow.

## Change

Delete `proposal_lane` from local roles, schemas, routing, tests, and docs. Classify proposal targets only at the publication boundary as `proposal_ref`; add no replacement state or command.
