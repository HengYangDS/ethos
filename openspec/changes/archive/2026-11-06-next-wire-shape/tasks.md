# Tasks

## 1. The next-step vocabulary

- [x] 1.1 Specify the vocabulary with failing tests: authorization kinds, effects, destructive rows,
      opaque steps, a decision that carries its argv, and a refused carried `embedded`. Done when
      they fail on the current code. Red at 05:59:35: 26 kernel tests failed on the missing fields
      and kinds.
- [x] 1.2 Add the fields, the derivation table and the decision argv, and regenerate the result
      schema. Done when the kernel result tests pass. Green at 06:02:52: 498 kernel tests pass, the
      schema comparison included.

## 2. Retirement receipts

- [x] 2.1 Specify with failing tests that the retirement dry run's continuation carries `--retire`
      and is destructive, and that a mismatch either way blocks before any peer effect. Done when
      they fail on the current code. Red at 06:04:56: 15 failed; the continuation lacked `--retire`,
      and a publication receipt applied with it.
- [x] 2.2 Check `--retire` against the replayed receipt and put it in the continuation. Done when
      the publication tests pass. Green at 06:16:09: 230 land and publication tests pass.

## 3. Candidate refresh

- [x] 3.1 Specify with a failing test that a refresh whose old candidate head accepted does not
      contain refuses without `--confirm-irreversible`, and proceeds with it. Done when it fails on
      the current code. Red at 06:17:57: the preview's next action lacked `--confirm-irreversible`.
- [x] 3.2 Add the refusal and the flag. Done when the candidate projection tests pass. Green at
      06:20:15: 46 candidate projection tests pass.

## 4. Pins and documentation

- [x] 4.1 Pin that `prove --host --execute --full --json` exits 1 on `block` and on `unknown`, and
      that hook admission's readers do not widen. Done when those tests pass. Green at 06:20:53: 26
      host proof and boundary tests pass. The CLI, kernel, lane and hook areas then passed 2,293 at
      06:37:33; their 10 publication failures were `runtime_build_stale` from formatting edits
      during that run, and those 62 tests pass on a clean rerun at 06:41:18.
- [x] 4.2 Write the schema-3 CHANGELOG entry and update the command-plane reference. Done when the
      Markdown checks and strict OpenSpec validation pass. At 06:24:18 strict validation passed 12
      of 12 specs after a simulated archive; Prettier and Vale pass on the seven Markdown files.
