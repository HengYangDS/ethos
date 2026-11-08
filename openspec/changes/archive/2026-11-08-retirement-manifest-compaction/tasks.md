# Tasks

## 1. Manifest

- [x] 1.1 Move the reviewed nodes to a content-addressed manifest that derivation writes before the
      request. Done when a test shows that a reviewed request and its receipt carry only the
      manifest digest, size and per-root totals, and the manifest file holds every node. At 07:51:44
      the new manifest tests could not import the manifest module; at 07:54:38 the 14 manifest tests
      passed, among them the reviewed request that keeps only the reference while the manifest file
      holds every node.
- [x] 1.2 Load the manifest at admission and removal. Done when a test shows that a missing or
      altered manifest refuses before any removal with its gap and selects a fresh content review,
      and the existing content drift and open-file tests still pass. At 07:54:38 the missing and
      altered manifest cases refused removal with `lane_retirement_manifest_missing` and
      `lane_retirement_manifest_mismatch` and returned the fresh content review, and at 08:00:55 the
      359 lane retirement, CLI retirement and Attestation command tests passed, the content drift
      and open-file tests among them.
- [x] 1.3 Release the manifest after the terminal receipt. Done when a test shows that a terminal
      retirement deletes its manifest, and a manifest that another unreceipted request binds
      survives the first request's terminal. At 07:54:38 a terminal retirement deleted its manifest
      and reported it, and a manifest that a second unreceipted request bound was kept.
- [x] 1.4 Continue an inline request through a fresh admission. Done when a test shows that recovery
      of a request with inline nodes returns the fresh content review for its target instead of an
      empty next action. At 07:54:38 an inline request's recovery refused with
      `lane_retirement_receipt_invalid` and returned the fresh content review of the same branch.

## 2. Store check

- [x] 2.1 Check the local store for inline requests that still bind live carriers. Done when a
      read-only check over the Git-common store's lane retirement requests names every request with
      inline nodes and no terminal receipt whose worktree, ref or Lease still exists, or reports
      none. At 08:05:07 a read-only scan of the Git-common store read 337 terminal receipts and 212
      lane retirement requests with inline nodes, and none of the unreceipted ones still had a
      worktree, ref or Lease.

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. The precheck's 18 impacted test files passed at 08:09:13, 465 tests, its static checks
      finding only spec lines copied verbatim from the current requirements; readiness passed its 28
      gates at `df8183ff5` at 08:11:21.
