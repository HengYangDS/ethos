## MODIFIED Requirements

### Requirement: Patch admission reports every refused reference

Patch admission SHALL report every product reference of a patch that its baseline does not own,
in stable order, so that one admission names every declaration the repository lacks. It SHALL
read the patch's postimage from a workspace in which every path that the patch names shows the
patch, wherever the process's temporary directory lies. It SHALL refuse a patch that leaves a
named path as it was or makes one anything but a regular file.

#### Scenario: A patch consumes two unowned references

- **WHEN** a patch adds two references that no baseline owner admits
- **THEN** the admission names both refusals
- **AND** the first one remains its reason

#### Scenario: The temporary directory lies inside another checkout

- **GIVEN** the process's temporary directory lies inside the work tree of another repository
- **WHEN** a patch adds a reference that no baseline owner admits
- **THEN** the admission refuses it with the reason that it gives when the temporary directory
  lies outside every repository

#### Scenario: Git leaves the workspace as it was

- **WHEN** Git reports success for the patch and a path that the patch names is as it was
- **THEN** the admission refuses with `prewrite_patch_postimage_failed`

#### Scenario: A patch makes a named path a link

- **WHEN** a patch creates a symbolic link or a submodule entry at a path that it names
- **THEN** the admission refuses with `prewrite_patch_postimage_failed`
