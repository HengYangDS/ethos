## 1. Contract and RED

- [x] 1.1 Add a regression that reproduces CRLF normalization under
  `core.autocrlf=true` and requires repository-local byte preservation.
- [x] 1.2 Add a contract assertion that repository hygiene belongs to the full
  proof set.

## 2. Unique owner repair

- [x] 2.1 Declare the fixture-specific line-ending policy in the generated
  adopter repository.
- [x] 2.2 Replace the four test-only type suppressions with explicit typed
  boundaries.
- [x] 2.3 Register the existing repository-hygiene owner in the full proof set.

## 3. Closure

- [x] 3.1 Pass strict OpenSpec validation and focused regression tests.
- [x] 3.2 Pass repository hygiene, Ruff, types, and exact-HEAD full proof.
- [x] 3.3 Freeze a signed source commit with a clean worktree and exact-HEAD
  full proof before archive.
