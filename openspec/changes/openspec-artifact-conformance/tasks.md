# Tasks

## 1. Template Structure

- [x] 1.1 Add `status --all` and the per-schema `templates` read to the governance report's read batch; verify a fixture root with two active Changes returns both artifact graphs and one template set.
- [x] 1.2 Report each missing or misordered literal template heading in an active proposal or design; verify regressions for a missing `Risks / Trade-offs`, a misplaced `New Capabilities`, an added `Migration Plan` without a gap, and a template that gains a heading.

## 2. Length Boundary

- [x] 2.1 Limit the document-length exemption to the immutable archive root and accepted specifications; verify a 513-line active design and delta spec are reported, and a 513-line accepted specification and archived design are not.
- [ ] 2.2 After `proof-throughput` archives, add the `quality` delta that modifies "Current Markdown stays within one navigable topic" for active Change artifacts; verify `openspec validate --all --strict` passes.

## 3. Archive Readiness

- [x] 3.1 Archive the active Change that the proof selects with the official CLI in a disposable projection of the exact head and run strict specification validation before proof gates; verify a MODIFIED requirement of 501 characters fails proof before any gate runs, the projection is removed, and the repository tree is unchanged.

## 4. Fleet Conformance

- [ ] 4.1 Run every check with this lane's runtime against the dev head of every governed repository and report each gap to its repository owner; verify each reported gap names its artifact and owner.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
- Adopters rebind to a runtime with these checks on their own schedule, after their owners clear the gaps reported in 4.1.
