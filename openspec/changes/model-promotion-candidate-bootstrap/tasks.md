# Tasks

- [x] **1. Reproduce candidate bootstrap rejection.** Cover exact terminal-v1
  candidate bytes and a v2 desired head.
- [x] **2. Reuse bootstrap admission.** Carry the existing exact prestate fields
  in candidate integration plans.
- [x] **3. Prove the bounded implementation.** Run focused landing tests,
  OpenSpec, type, and size checks.

| Outcome | Task | Evidence |
| --- | ---: | --- |
| `command-plane:Candidate integration admits exact repository bootstrap` | 1 | `tests:candidate-bootstrap-land` |
| `adapters:Repository identity remains fail-closed` | 2 | `tests:git-effect-repository-identity` |
| `quality:Bootstrap closeout is proven` | 3 | `proof:exact-head` |
