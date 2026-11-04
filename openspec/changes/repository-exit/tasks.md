# Tasks

## 1. Preimage

- [x] 1.1 Record, at install, the hooks-related configuration that install replaces, in both scopes.
      Done when tests show three things: a first install over a pre-ETHOS hooks path records it;
      a first install over no hooks path records its absence; and a re-install leaves the record
      byte-identical. Evidence: the install tests in `tests/unit/adapters/repo/hook/test_exit.py`.

## 2. Exit preview

- [x] 2.1 Add `ethos adopt --exit` as a read-only preview. Done when tests show the planned
      restoration and selector hashes, a stable plan digest that binds the Lease snapshot, the
      user decision required without a record, the blocking of a valid Lease, the refusal of an
      apply as `adoption_exit_apply_unavailable`, and no file changed by the preview. Evidence:
      the preview and CLI tests in the same file.

## 3. Specification and notes

- [ ] 3.1 Write the `runtime-activation` delta and the command reference. Done when strict
      validation and the cumulative archive simulation pass.
