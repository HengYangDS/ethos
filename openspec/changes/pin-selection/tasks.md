# Tasks

## 1. Pin selection

- [x] 1.1 Add the decision `follow_accepted_pin` and its fixture-adopter regression. Done when the
      regression fails before the module exists and passes after it, and shows each of
      `runtime_pin_absent`, `runtime_pin_behind_current`, `runtime_pin_unattested` and
      `runtime_pin_not_installed`, a checksum-class entry selected without provenance, and an
      adopter with and without a pin.
- [x] 1.2 Route hook activation and `adopt --select-runtime` through the decision. Done when a
      fixture adopter's activation selects the pinned install through the declaration preflight,
      a kept selection is neither rebuilt nor pinned again, and the adoption plan names the pin's
      state.
- [x] 1.3 Add `--reason` to `hook install` and the lane-bound receipt. Done when a regression reads
      the receipt before the first effect, shows both kinds, the refusal without a reason or a lane,
      and closure by a changed pin and by a retired lane.

## 2. Rollback proof

- [x] 2.1 Prove a predecessor before pinning it or writing `ROLLBACK`. Done when a predecessor that
      no install of the root would admit is reported as `unrunnable` with the install's gap, stays
      out of the host store and leaves no `ROLLBACK`.
- [x] 2.2 Report an unrunnable held rollback in `status` with one repair. Done when `status` names
      the gap and the CURRENT console's `hook install` for a rollback whose bytes are gone and for
      one of a build the accepted source does not admit, and that install releases the selector and
      reports it.

## 3. Documents

- [x] 3.1 Describe the pin, the receipt and the rollback proof in the local-state architecture
      document, and add the changelog entry. Done when Prettier and the prose gate pass on both
      files.

## 4. Acceptance

- [ ] 4.1 Pass the focused gates on the lane head: the unit modules that import a changed module,
      Ruff, ty, import-linter, `openspec validate pin-selection --strict` and Prettier. Done when
      each reports no finding.
- [ ] 4.2 Measure the source budget against the lane base. Done when the measured figures are
      recorded: product +281.0 and tests +447.2 line-equivalents over `23538df6b` on the lane's own
      commits, against the design's about 275 and 440; the difference is the regression and the
      wiring of task 5.3.

## 5. Lane, hosted and owner tasks

- [ ] 5.1 Apply this Change on C1's landed `release/pin.py` and remove the stand-in. Done when the
      regressions pass against C1's readers and the budget of 4.2 is measured on the lane's commits.
- [x] 5.2 Register the gap codes this Change raises with the gap-code table. Done when its static
      test passes with `runtime_pin_unattested`, `runtime_pin_not_installed`,
      `runtime_selection_receipt_required` and the pin reader's gaps that a transition raises again.
- [x] 5.3 Name the pin's next action in the `hook install` result's `next`, after the Change that
      rewrites that result has landed. Done when a regression reads it from `next`.
- [ ] 5.4 Pass the precheck, readiness and one proof on the committed lane head. Done when each
      passes.
- [ ] 5.5 Check `mise where` for the pin against a release that C1's hosted journey installed. Done
      when the answer names one `runtime/<16 hex>` generation that the activation selects.
- [ ] 5.6 Keep the command reference's runtime selection section free of a second copy of the
      local-state rules. Done when the section names the selection and the pin without restating
      them and the page stays within its line bound.

## Workflow follow-up

- Point the command reference's runtime selection section at the local-state document when the page
  has room under the document length ceiling.
