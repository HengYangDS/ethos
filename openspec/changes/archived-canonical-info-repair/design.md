# Design

## Context

The active-Change INFO repair uses the official validation envelope. The archived repair path currently admits only invalid specs with exit code 1 and assumes one gap per file. A valid archive output can instead produce several INFO findings in one canonical file with exit code 0.

## Decisions

- Reuse the existing official-validation parser to identify valid INFO findings and their unique canonical capability paths. Do not parse warning prose or infer ownership from filenames.
- Resolve the prior archive through its validated effect Attestation, then intersect its authorized outputs with those exact regular files. This also admits two findings in one file without multiplying write authority.
- Keep the repair scope separate from ordinary status, proof and commit satisfaction. Status may point to the corrective prewrite; only fresh warning-free validation restores normal admission.

## Risks and verification

- A forged or stale archive/validation envelope could overgrant a path: reject it at the existing evidence and exact-output checks.
- A narrower repair could still dead-end on multiple INFO findings: exercise two findings in one spec through public status and prewrite, alongside wrong-file, missing archive and ordinary-proof counterexamples.

## Migration

Install the accepted immutable runtime, rebind affected adopters through their normal update path, then apply the already prepared canonical correction under fresh prewrite. No warning policy, history or stored intent migration is required.
