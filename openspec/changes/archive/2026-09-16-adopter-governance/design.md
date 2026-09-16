## Context

An isolated Node adopter executed real installed-runtime proof and candidate
CAS with contradictory protected branch declarations. The equivalent registry
profile instead failed prewrite with `root_binding_mismatch`. Original public
evidence is retained under `build/evidence/quality/commit-integrity/` as
`inline-public-probe-*.json`; it is attributed to its original source, not
presented as a new run. Current accepted `00881b77` retains the owning paths.

`domain/status.py` dispatches on registry presence and otherwise manufactures a
passing OpenSpec observation. `runtime/binding.py` uses that same storage detail
to require checkout equality, and guesses schema origin from adopter files.
The schema loader actually selects runner-owned source or package schemas.
Release configuration mixes generic role consistency with product-only version,
file and attestation requirements.

## Decisions

1. Common governance evaluates applicable declarations for every adopter.
   Gate representation cannot enable, disable or broaden these obligations.
   Observe OpenSpec through its existing owner rather than a capability boolean.
2. Release configuration owns parsing and role consistency. Absence remains
   optional; malformed present input blocks. Compare protected branch membership
   with the configured role policy, not hardcoded branch names or list order.
   Product-specific release requirements reuse this result instead of copying it.
3. Product conformance is an explicit provider invocation, not a repository type
   guessed from names, paths or registry presence. The generic public audit and
   actual integration effects retain common invariants. The accepted predecessor
   retains its verification floor during control replacement; a candidate cannot
   opt out by editing its gate declaration. The common `repository-audit` gate
   stays generic; the existing `product-boundary` gate explicitly composes ETHOS
   conformance. Replacing or removing a required predecessor gate descriptor
   requires the existing independent-verification receipt even when the ordinary
   control profile is disabled. Descriptor preservation is not a proof that
   changed verifier implementation is independently trustworthy.
4. Runtime diagnostics consume the schema loader's selected provenance and the
   existing selected-runtime observation. Package schemas need not belong to the
   adopter checkout. Preserve source-bound execution and control-replacement
   safeguards; do not grant mutation merely because a profile parses.
5. Preserve observation scope: status readiness is not full Change completion;
   passing fixture tests are not packaged, installed or remote acceptance.

## Execution Order

First extract and test the generic declaration invariant at its release owner.
Then compose common versus product audit and correct runtime provenance, keeping
trusted prior checks and migrating consumers together. Replay equivalent inline
and registry fixtures through public commands, positive and negative paths.
Freeze the candidate for focused quality followed by exact full proof, official
archive, postarchive proof, acceptance and runtime activation. Let adopter owners
update and replay their own repositories.

## Verification

- A valid minimal Node repository succeeds without ETHOS product files.
- Equivalent inline/registry gates yield equivalent common audit and prewrite.
- Contradictory roles, malformed release/commit declarations and real OpenSpec
  errors reject before the relevant effect; the target ref remains unchanged.
- Absent optional policies do not impose product-specific defaults.
- Reordered valid protected branches retain their meaning; duplicate or wrongly
  typed declarations fail precisely.
- Selected package schemas are reported truthfully; foreign/stale runners and
  attempted candidate verification downgrades remain rejected.
- The existing self-product audit, source schema validation and lifecycle suite
  retain their acceptance coverage after dispatch migration.

## Boundaries

No compatibility exports or alternate parser. No new persistent policy database,
adopter patch or named-repository exception. Native commands, exact source/tree,
policy inputs and result artifacts establish each claim independently.
