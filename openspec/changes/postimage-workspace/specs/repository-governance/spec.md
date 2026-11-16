## MODIFIED Requirements

### Requirement: Patch admission reports every refused reference

Patch admission SHALL report every product reference of a patch that its baseline does not own,
in stable order, so that one admission names every declaration the repository lacks. It SHALL
read the patch's postimage in a workspace that Git treats as no part of any repository, wherever
the process's temporary directory lies.

#### Scenario: A patch consumes two unowned references

- **WHEN** a patch adds two references that no baseline owner admits
- **THEN** the admission names both refusals
- **AND** the first one remains its reason

#### Scenario: The temporary directory lies inside another checkout

- **GIVEN** the process's temporary directory lies inside the work tree of another repository
- **WHEN** a patch adds a reference that no baseline owner admits
- **THEN** the admission refuses it with the reason that it gives when the temporary directory
  lies outside every repository
