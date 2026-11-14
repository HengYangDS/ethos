## ADDED Requirements

### Requirement: A denied placement admits its own removal

When the artifact topology denies a path's placement, write admission SHALL refuse a creation or
an edit of that path with the placement's gap, and SHALL admit the removal of a tracked path
there under the checks that every tracked removal passes. The removal is observed, not declared:
a tracked path absent from the worktree for a worktree request, and the `delete` effect for an
index request. A rule that says a path does not belong SHALL NOT also forbid taking it away.

#### Scenario: A tracked file under a denied prefix is deleted

- **WHEN** a Work Lane removes a tracked file under a prefix that the topology denies and asks
  for a prewrite decision, or stages the deletion
- **THEN** the placement does not refuse the path
- **AND** the ordinary scope and role checks decide the request

#### Scenario: A file under a denied prefix is created or edited

- **WHEN** a request creates a path under a denied placement, or names a path there that is
  still present
- **THEN** admission refuses it with the placement's gap
