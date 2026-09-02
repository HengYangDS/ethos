## 1. Reference Semantics

- [x] 1.1 Add a regression proving canonical OpenSpec absence requirements do
  not consume retired paths, and verify it fails for the current implementation.
- [x] 1.2 Add a regression proving canonical OpenSpec links still consume
  retired paths, and verify it passes only with the intended syntax boundary.
- [x] 1.3 Make Markdown path consumption uniformly link-based without adding a
  keyword classifier or exception list, and verify focused closure tests pass.

## 2. Closeout

- [x] 2.1 Verify strict OpenSpec validation, repository-wide semantic closure,
  formatting, and the focused regression set.
- [x] 2.2 Bind the complete source, tests, and official artifacts in one signed
  commit so lifecycle closeout can run exact-HEAD proof, archive, post-archive
  proof, and candidate/accepted CAS without another semantic edit.
