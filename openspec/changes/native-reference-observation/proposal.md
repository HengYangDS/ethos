# Proposal

## Why

Patch admission discovers Python command owners by parsing every carrier as Python, then parses
selected Python carriers again. This repeats work on fresh inputs and manufactures fragment trees
for Markdown, JSON and malformed source without improving the required observation.

## What Changes

- Classify carriers through the existing native carrier owner before parsing.
- Share complete Python trees within one invocation across command and reference observations.
- Remove redundant Python forwarding helpers and fragment recovery from complete-carrier observation.
- Preserve unknown-carrier results and all fresh repository admission reads.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is an implementation simplification of existing reference-observation contracts.

## Impact

The existing reference observer and its admission consumers change internally. Public reports,
repository policy, dependencies, Git freshness, signatures and mandatory gates remain unchanged.
No adopter runtime is activated, and release coordination holds remain in force.
