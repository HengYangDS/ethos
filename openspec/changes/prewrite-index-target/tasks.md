# Tasks

## 1. Exact index admission

- [x] 1.1 Reproduce incumbent rejection and mixed-prestate RED; preserve `review1/red.xml`.
- [x] 1.2 Extend staged admission and its target flag; pass 20 preservation tests in 250 lines.
- [x] 1.3 Align the public contract; pass default-target and 129 directly affected sibling tests.

## 2. Consumer qualification

- [x] 2.1 Replay exact adopter patches read-only; report preserved state and gaps in `review1/`.
- [ ] 2.2 Pass original formatters, strict OpenSpec and relevant gates; verify cleanup and scope.

## Workflow follow-up

- Refresh after `record-retirement-apply` lands, before proof through an authorized
  native transition; preserve the prior signed implementation in Git.
- Freeze and sign the reviewed source; run the exact-HEAD full proof under the
  host proof slot without treating prior focused tests as full acceptance.
- Notify the owner before land or closeout so only one land chain runs at a time.
- Publish and land through the normal reviewed route after that base refresh.
- Post-release adopter follow-up belongs to each adopter's owning agent:
  rerun its exact stage-preview patch read-only under the released runtime,
  verifying unchanged source, unrelated staging and working content before a
  separately authorized binding; preserve its declared rollback runtime.
- Archive through the native continuation only after this Change closes.
