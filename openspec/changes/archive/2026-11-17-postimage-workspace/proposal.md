# Proposal

## Why

`ethos lane prewrite --patch` judges a patch by its postimage. It copies the files that the patch
names into a temporary workspace, applies the patch there with Git and reads the result. When the
process's temporary directory lies inside a Git work tree, Git takes the workspace for a
subdirectory of that work tree, skips every path of the patch as lying outside it and reports
success. The admission then reads the unchanged copies, the preimage, as the postimage.

Measured on 2026-11-16 with one patch and one repository, the temporary directory outside every
repository and then inside an ignored directory of another one, on the installed 0.2.0-beta.9 and
0.2.0-beta.10 and on the source of the accepted head:

- A patch that adds an undeclared executable to a script is refused outside and admitted inside.
- The move of a dated active Change to its logical name is admitted outside and refused inside
  with `prewrite_patch_postimage_failed`.
- Of 168 tests of six admission modules, 17 fail inside: twelve admit what they must refuse and
  five refuse what they must admit.

The module is the same file in 0.2.0-beta.10 and at the accepted head, and the workspace came
with 0.2.0-alpha.5. The default temporary directory of macOS and of Linux lies outside every
repository, so a default host does not meet the defect. A host, an agent sandbox or a pipeline
that sets its temporary directory inside a checkout does. The first end-to-end run of the
hermetic journey did: it gives each stage a temporary directory under the checkout, and each of
its three legs failed at the retained Change's move.

The repair is admitted by the batch's own acceptance, because the journey tasks of
`hermetic-journey` and `journey-hosts` need a journey that passes, and by the owner's standing
direction of 2026-11-14 to repair a defect of the base as an invariant. It is one more measured
case of the class that the draft `gate-environment` collects, a local verdict that follows the
launching environment.

## What Changes

- Patch admission applies a patch in a workspace that is a repository of its own, wherever the
  process's temporary directory lies, and refuses a patch that declares a symbolic link or a
  submodule entry.

Not breaking: on a host whose temporary directory lies outside every repository nothing changes.
On a host whose temporary directory lies inside one, an admission that was wrong becomes right:
some patches that passed are now refused, and the dated Change's move passes. A patch that
declares a link was admitted without what the link names being read, and is now refused on
every host.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: one requirement is added, with four scenarios:
  `Patch admission reads what a patch does from Git`. It stands beside
  `Patch admission reports every refused reference`, whose words do not change. OpenSpec bounds
  a requirement's text at 500 characters, and the two are separate behaviors.

## Impact

`src/ethos/adapters/admission/patch_admission.py` and the workspace's new module
`src/ethos/adapters/admission/patch_workspace.py`; one regression in
`tests/unit/admission/test_patch_admission_public_fail_closed.py`;
`openspec/specs/repository-governance/spec.md` through this Change's delta, and `CHANGELOG.md`.

Out of scope: where the hermetic journey places a stage's directories, which is that Change's;
the other cases of `gate-environment`; and the releases that hold the defect, whose entries are
their release Changes'.
