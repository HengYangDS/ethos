# Tasks

## 1. Grammar

- [x] 1.1 Add `style` to the commit types of the paradigm contract. Done when commit admission
      accepts `style: reformat`, accepts `style(cli): reformat` under the declared scopes `cli`
      and `relay`, still rejects `spec(cli): add`, and the tests of the paradigm contract and of
      the commit policy pass.
      (In `011daf51f`: the commit policy's cases hold the three subjects, with and without the
      declared scopes. Both test modules pass in the full proof of `7bd573ad9`.)
- [x] 1.2 State the change in the changelog under Changed and name `style` in the contributing
      guide's list of types. Done when the changelog reader accepts the file and the guide
      names eleven types.
      (In `011daf51f`. The changelog's reader and the documentation registry pass in the full
      proof of `7bd573ad9`.)

## 2. Lane only

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
      (At `7bd573ad9` on 2026-11-20 the pre-check passes with no finding and readiness passes with
      its 28 gates. The pre-check ran its full selection at `a9e90ab6f`, 413 test modules, 8,337
      passed and 3 skipped, and from there the selection of the one test file that differs, 43
      modules, 371 passed and 1 skipped.)

## 3. After the release

- [ ] 3.1 Read one governed repository whose lane holds commits with the type `style` under the
      release that carries this Change. Done when its landing preview names no
      `commit_subject_invalid` for those commits.
