# Design

Local authoring has one role: `work_lane`. `proposal/*` is not a checkout authority. Publication recognizes the configured proposal prefix directly, requires the exact candidate source, and executes the existing exact-object CAS path.

The change deletes the mixed role rather than renaming it globally. The only remaining label, `proposal_ref`, is an output classification of publication admission.
