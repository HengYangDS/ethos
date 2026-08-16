# Repair the accepted signature suffix

## Why

The accepted suffix after `8840e35d282e6d9ea4c32652c3d03491e3d52e16`
contains one unsigned lifecycle materialization commit. The generation defect is
already fixed and accepted, but publication provenance remains incomplete until
the historical suffix is replaced by its exact-payload signed identity train.

## What Changes

- Consume the accepted public `lane repair-identity` capability.
- Derive one immutable receipt for the exact linear suffix.
- Apply one exact-CAS replacement across the observed work, candidate,
  accepted, and release refs.
- Re-prove the rewritten HEAD before normal archive, land, and closeout.

## Boundaries

This Change adds no product behavior or specification delta. It does not modify
AIGW or Proxy, broaden history-rewrite authority, repair runtime portability,
or change adopter profile compatibility.
