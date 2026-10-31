# Tasks

## 1. Removals

- [x] 1.1 Remove the eight product pass-throughs and two assignment aliases the proposal lists, and
      move their callers, patches and test imports to the owners. Done when none of the removed
      names is defined or imported anywhere and the affected tests pass.
- [x] 1.2 Remove the renaming aliases, renaming the owners where the proposal names a new owner
      name, and import every name from its defining module. Done when the inventory's renaming-alias
      and indirect-import sites are gone and the affected tests pass.

## 2. Checks

- [x] 2.1 Make module-layout refuse a renaming from-import alias and an import through a governed
      module that does not define the name, with red and green tests. Done when both red cases fail
      the gate, both green cases pass, and module-layout passes on the lane head.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to the peers that answer.
