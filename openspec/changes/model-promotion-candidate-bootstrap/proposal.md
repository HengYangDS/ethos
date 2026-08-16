# Change: Carry repository bootstrap identity into candidate landing

## Why

The repository Commitment was publicly bootstrapped from terminal v1 to v2 in
the owner lane, while `candidate/dev` still carried the exact v1 bytes. Landing
compiled a normal candidate effect and the shared repository-identity admission
correctly rejected the schema transition as an identity mismatch.

## What Changes

- Recognize an exact terminal-v1 repository Commitment at the candidate head.
- Reuse the existing repository bootstrap policy fields with its exact ID and
  byte digest when compiling candidate integration.
- Preserve the normal transition for valid v2 carriers and reject malformed or
  missing prestate carriers.

## Impact

- Affected code: candidate landing plan compilation and its focused contract test.
- No new permission, compatibility reader, state store, or generic identity bypass.
