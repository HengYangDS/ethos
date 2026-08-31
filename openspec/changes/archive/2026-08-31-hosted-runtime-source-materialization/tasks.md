## 1. Preserve the authority failures

- [x] 1.1 Add a product-resolver regression proving Windows uses package-root
  `node.exe` and every build consumer receives the same validated Node/npm
  coordinates.
- [x] 1.2 Add a Hosted projection regression proving repository proof configures
  required Git identity but never activates Git-common hooks or runtimes.
- [x] 1.3 Add a repository-audit regression proving source correctness is
  independent of local hook/runtime currentness.

## 2. Replace the duplicate owners

- [x] 2.1 Move Node/npm package-layout resolution into the existing runtime
  input owner, migrate OpenSpec and delivery consumers, delete the CI-only
  helper, and prove repository-wide reference closure.
- [x] 2.2 Remove hook/runtime activation from both Hosted proof projections and
  remove local hook state from repository source audit while preserving status
  and mutation admission ownership.

## 3. Prove and close the change

- [x] 3.1 Pass focused unit and architecture tests plus CI projection drift and
  strict OpenSpec validation.
