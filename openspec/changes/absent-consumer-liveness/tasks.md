# Tasks

## 1. Liveness

- [ ] 1.1 Treat a missing consumer path as unknown liveness and list it in the retention report.
      Done when the host-retention tests show that an installation recorded only by a repository
      whose directory is gone stays, its record stays, and the report's `absent` names that
      repository.
