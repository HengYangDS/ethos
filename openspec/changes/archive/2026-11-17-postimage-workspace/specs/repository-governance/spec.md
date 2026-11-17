## ADDED Requirements

### Requirement: Patch admission reads what a patch does from Git

Patch admission SHALL read the patch's postimage in a workspace that is a repository of its own,
wherever the process's temporary directory lies. It SHALL take what a patch does at each path,
and the kind of each entry, from Git's own record of the patch applied in that workspace, and
SHALL refuse a patch that makes another kind of entry than a regular file. The request of a
patch SHALL name every path that Git changes, the source of a move among them.

#### Scenario: The temporary directory lies inside another checkout

- **GIVEN** the process's temporary directory lies inside the work tree of another repository
- **WHEN** a patch adds a reference that no baseline owner admits
- **THEN** the admission refuses it with the reason that it gives when the temporary directory
  lies outside every repository
- **AND** the same holds where that directory's name contains the separator of a path list

#### Scenario: A patch declares a link

- **WHEN** a patch declares a symbolic link or a submodule entry at a path that it names
- **THEN** the admission refuses with `prewrite_patch_postimage_failed`

#### Scenario: A patch moves a file that another file still reads

- **GIVEN** a request that names the move's source and its target
- **WHEN** a patch moves a file, and a file that the patch does not change still imports the
  source
- **THEN** the admission reads the source as deleted
- **AND** it refuses with the reason of a deleted input

#### Scenario: A request names a move's target alone

- **WHEN** a patch moves a file and the request names the target and not the source
- **THEN** the admission refuses with `prewrite_patch_paths_mismatch`
- **AND** its report names both paths
