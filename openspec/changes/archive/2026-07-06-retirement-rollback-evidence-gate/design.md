# Design

`ethos fleet retirement-readiness --target <repo> --json` now treats rollback
window evidence as a generic profile-driven precondition. The gate becomes
applicable only after parity and shadow checks pass, the external backend is in
a default-or-later state, and the embedded backend is frozen as fallback or
reference.

When applicable, ETHOS reads `[rollback_window]` from `.ethos/profile.toml` and
requires:

- `state = "complete"`;
- `evidence_manifest` pointing at a tracked adopter repository path;
- completed standard scenarios: `proof_report`, `work_lane_closeout`,
  `domain_gate`, and `assistant_playbook`.

The standard scenario list is a floor. Adopter profiles may add required
scenarios, but omitting the standard scenarios does not weaken the product gate.
The report emits `retirement_rollback_window_*` gaps and
`state = rollback_window_evidence_open` when profile state claims terminal
readiness without the evidence floor.
