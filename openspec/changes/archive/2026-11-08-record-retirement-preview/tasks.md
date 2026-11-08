# Tasks

## 1. Parameters and refresh

- [x] 1.1 Declare the `retention` group with floor rows. Done when a test shows that a higher
      `retention.record_seconds` applies without a reason, a lower one is a gap that keeps the
      default, and the existing parameter tests still pass. At 09:09:49 the retention floor cases
      failed for want of the `retention` group; at 09:10:24 a raised `record_seconds` applied
      without a reason, a lowered one and one beyond the bound were gaps that kept the default, and
      at 09:21:13 the 349 parameter, paradigm and hook tests passed.
- [x] 1.2 Refresh the mtime of an identical content-addressed write. Done when a test shows that
      writing identical bytes again moves an old file's mtime to now and a differing payload still
      refuses. At 09:09:49 an identical write left the old mtime; at 09:10:24 it moved the mtime to
      the write and a differing payload still refused.

## 2. Preview

- [x] 2.1 Classify the allowlisted kinds. Done when a test on a fixture store classifies each
      artifact writer's record, the terminal, receipt-only and manifest-only lane retirement units,
      and reports a foreign file under an owned name by path and bytes. At 09:14:07 the kind, roots,
      preview and CLI tests could not import the retention modules; at 09:18:58 the fixture store's
      proof-check document, merge preimage, native and JavaScript attempt archives and terminal,
      receipt-only and manifest-only units took their kinds, and a foreign artifact was reported by
      path and bytes.
- [x] 2.2 Keep every item a root names. Done when a test shows that a digest inside zip, gzip, tar
      or base64 content of a kept file, in a live Attestation member or in the accepted tree keeps
      its item and the items it names, and that a carrier beyond the decode bounds refuses. At
      09:18:58 a digest in plain, zip, gzip, tar, base64 and nested content was read, a custody
      record named an archive that named a merge preimage and both were kept, an accepted-tree note
      and a live member each kept the record they named, and carriers beyond the depth or the budget
      and damaged archives refused.
- [x] 2.3 Admit, select and write the plan. Done when a test shows that an unselected runtime, an
      unreadable accepted floor and a held proof slot each refuse and write nothing, that a young
      item is kept, and that the plan names the accepted commit, the cutoffs and each candidate. At
      09:18:58 another runtime, an unparsable accepted binding, a held proof slot and an undecodable
      kept carrier each refused and wrote no plan, a young record was kept, and the plan named the
      accepted commit, both cutoffs and each candidate's files with sizes and mtimes.
- [x] 2.4 Expose `ethos hook retire-records`. Done when a CLI test shows the preview's structured
      result with candidate counts and bytes per kind and the plan's path and digest. At 09:18:58
      `ethos hook retire-records --json` reported state `planned` with candidate counts and bytes
      per kind and the plan's path and digest, and deleted nothing.

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. The precheck's 354 impacted test files passed at 09:47:11, 5,529 tests with 4 skipped,
      with no static findings; readiness passed its 28 gates at `fb67c1756` at 09:48:59.
