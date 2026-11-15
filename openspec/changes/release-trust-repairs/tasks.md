# Tasks

## 1. Pin selection

- [ ] 1.1 Require the lock entry of the host's platform in every class, and its checksum in the
      checksum class. Done when the cases `checksum-no-lock`, `checksum-no-entry` and
      `checksum-no-sum` of `tests/unit/adapters/repo/runtime/test_pin_selection.py` name
      `runtime_pin_unattested`, after each selected the install, and the case `checksum-class`
      still selects.

## 2. Shared conformance

- [ ] 2.1 Require the exact planned files of an adoption in the shared CLI, SDK and MCP
      conformance, with the pin only from a release build. Done when
      `test_shared_conformance_requires_the_exact_planned_files` passes its six cases, after the
      superset comparison accepted three that it should refuse, and
      `tests/unit/surface/mcp/test_stdio.py` passes from source.

## 3. Documents

- [ ] 3.1 State what `runtime_pin_unattested` covers in the checksum class in
      `docs/architecture/local-state.md`, and add the two entries to `CHANGELOG.md` under
      Unreleased, Fixed. Done when Prettier and the prose gate pass on both files.

## 4. Acceptance

- [ ] 4.1 Pass the focused gates: `tests/unit/adapters/repo/runtime/`, `tests/unit/ci/delivery/`,
      `tests/unit/release/`, `tests/unit/surface/mcp/test_stdio.py`, the architecture guards for
      decision density, parallel implementations, owned literals, the gap registry, the single gap
      transport, declared timeouts and product boundaries, Ruff, ty, import-linter,
      `openspec validate release-trust-repairs --strict` and Prettier. Done when each reports no
      finding.
- [ ] 4.2 Measure the three source budgets against the base. Done when the measured deltas are
      recorded with their reason.

## 5. Lane tasks

- [ ] 5.1 Apply on the lane head with the other review repairs of this batch, and merge by
      meaning the hunks in `CHANGELOG.md` and in any test module that another repair also
      edits. Done when the regressions of tasks 1.1 and 2.1 pass on the merged tree.
- [ ] 5.2 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.

## Workflow follow-up

- The release Change of 0.2.0-beta.11 reads back that the installed command plane stage of package
  acceptance passed on every release leg, where the exact planned-file list runs on a release
  build.
- `release-acceptance`, the Change that first calls the explicit release transition, decides and
  repairs a finding of the same review that this Change leaves: a version that is accepted again,
  once with its checksum file and once without, is admitted, because admission treats a missing
  binding as compatible; the transition then stores the wheel, gets the version's earlier record
  back from the Attestation set and refuses with `identity_transition_attestation_mismatch`.
  Nothing calls that transition in 0.2.0-beta.11. The choice is between refusing at admission
  and letting the recorded identity stand, which restates the requirement
  `Accepted release identity is immutable`.
