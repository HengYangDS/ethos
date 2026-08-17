## ADDED Requirements
### Requirement: Source runtime uses the locked closure
ETHOS SHALL install source-built runtimes from `uv.lock` offline.
#### Scenario: Lock unavailable
- **WHEN** the lock cannot supply the production closure
- **THEN** installation SHALL fail without fallback or network resolution.
