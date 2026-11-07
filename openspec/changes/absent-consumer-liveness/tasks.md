# Tasks

## 1. Liveness

- [x] 1.1 Treat a missing consumer path as unknown liveness and list it in the retention report.
      Done when the host-retention tests show that an installation recorded only by a repository
      whose directory is gone stays, its record stays, and the report's `absent` names that
      repository. At 17:11:51 `test_a_consumer_whose_path_is_gone_keeps_its_record_and_installation`
      passed with the other host-retention tests: the installation and its consumer record stay, and
      `absent` names the removed repository.
