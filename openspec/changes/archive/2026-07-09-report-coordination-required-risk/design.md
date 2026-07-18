# Design

Status owns Work Lane coordination truth. Report is a read-only scorecard over
that truth.

The reducer derives two buckets:

- required: coordination gaps already required by repository audit or workspace
  status;
- advisory: audit coordination signals and status advisories not present in the
  required bucket.

Required coordination gaps affect report `required_gaps`, next actions, and the
effective score across product and adopter profiles. Advisory gaps remain visible
under coordination/advisory layers and never authorize writes, land, retire, or
cleanup in foreign Work Lanes.

The split is profile-neutral governed-repository semantics: product and adopter profiles differ by proof depth and local quality floors, not by whether status-required coordination blockers are report-visible.
