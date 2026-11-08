# Tasks

## 1. Manifest

- [ ] 1.1 Move the reviewed nodes to a content-addressed manifest that derivation writes before the
      request. Done when a test shows that a reviewed request and its receipt carry only the
      manifest digest, size and per-root totals, and the manifest file holds every node.
- [ ] 1.2 Load the manifest at admission and removal. Done when a test shows that a missing or
      altered manifest refuses before any removal with its gap and selects a fresh content review,
      and the existing content drift and open-file tests still pass.
- [ ] 1.3 Release the manifest after the terminal receipt. Done when a test shows that a terminal
      retirement deletes its manifest, and a manifest that another unreceipted request binds
      survives the first request's terminal.
- [ ] 1.4 Continue an inline request through a fresh admission. Done when a test shows that recovery
      of a request with inline nodes returns the fresh content review for its target instead of an
      empty next action.

## 2. Store check

- [ ] 2.1 Check the local store for inline requests that still bind live carriers. Done when a
      read-only check over the Git-common store's lane retirement requests names every request with
      inline nodes and no terminal receipt whose worktree, ref or Lease still exists, or reports
      none.

## 3. Acceptance

- [ ] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
