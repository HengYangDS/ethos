# Tasks

## 1. Specification and regressions

- [x] 1.1 Record the proof terminal-seal and runtime-bound owner requirement
  in the OpenSpec delta.
- [x] 1.2 Add red regressions for gate ordering, test-gate EXIT cleanup,
  semantic type resolution, and shell portability.

## 2. Implementation

- [x] 2.1 Declare the topology gate after its runtime producers.
- [x] 2.2 Make denied runtime-residue cleanup symmetric at test-gate exit.
- [x] 2.3 Bind `ty` to the checkout semantic venv.
- [x] 2.4 Replace Bash-4-only path collection in affected owner scripts.

## 3. Verification and closeout

- [ ] 3.1 Run focused tests, owner quality gates, and strict OpenSpec
  validation.
- [ ] 3.2 Run owner quality gates and HEAD-bound proof.
- [ ] 3.3 Refresh required parity evidence, land only with live candidate proof, and retire this owned lane after formal closeout.
