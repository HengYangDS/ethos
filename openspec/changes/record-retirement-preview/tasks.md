# Tasks

## 1. Parameters and refresh

- [ ] 1.1 Declare the `retention` group with floor rows. Done when a test shows that a higher
      `retention.record_seconds` applies without a reason, a lower one is a gap that keeps the
      default, and the existing parameter tests still pass.
- [ ] 1.2 Refresh the mtime of an identical content-addressed write. Done when a test shows that
      writing identical bytes again moves an old file's mtime to now and a differing payload still
      refuses.

## 2. Preview

- [ ] 2.1 Classify the allowlisted kinds. Done when a test on a fixture store classifies each
      artifact writer's record, the terminal, receipt-only and manifest-only lane retirement units,
      and reports a foreign file under an owned name by path and bytes.
- [ ] 2.2 Keep every item a root names. Done when a test shows that a digest inside zip, gzip, tar
      or base64 content of a kept file, in a live Attestation member or in the accepted tree keeps
      its item and the items it names, and that a carrier beyond the decode bounds refuses.
- [ ] 2.3 Admit, select and write the plan. Done when a test shows that an unselected runtime, an
      unreadable accepted floor and a held proof slot each refuse and write nothing, that a young
      item is kept, and that the plan names the accepted commit, the cutoffs and each candidate.
- [ ] 2.4 Expose `ethos hook retire-records`. Done when a CLI test shows the preview's structured
      result with candidate counts and bytes per kind and the plan's path and digest.

## 3. Acceptance

- [ ] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
