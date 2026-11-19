# Tasks

## 1. Grammar

- [ ] 1.1 Add `style` to the commit types of the paradigm contract. Done when commit admission
      accepts `style: reformat`, accepts `style(cli): reformat` under the declared scopes `cli`
      and `relay`, still rejects `spec(cli): add`, and the tests of the paradigm contract and of
      the commit policy pass.
- [ ] 1.2 State the change in the changelog under Changed and name `style` in the contributing
      guide's list of types. Done when the changelog reader accepts the file and the guide
      names eleven types.

## 2. Lane only

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.

## 3. After the release

- [ ] 3.1 Read one governed repository whose lane holds commits with the type `style` under the
      release that carries this Change. Done when its landing preview names no
      `commit_subject_invalid` for those commits.
