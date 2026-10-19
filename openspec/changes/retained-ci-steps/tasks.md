# Tasks

## 1. Retention

- [x] 1.1 Declare the retention record's carrier, classes and platforms in the paradigm catalog and its declaration model; done when the packaged paradigm loads and refuses an unknown retention key.
- [x] 1.2 Admit an inline-shell CI step only through a complete, current retention record, and report `retained-step` for an incomplete record, an uncatalogued class or platform, a malformed digest and each listed job without the step; done when the scenario regressions in `tests/unit/repository/test_paradigm_orchestration.py` pass, including the YAML quoting and gate cases.

## 2. Documentation

- [x] 2.1 Record the retention boundary in DR-0012's consequence for scripts and in the changelog; done when the documentation checks pass.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish to both peers.
- aigw-cli and openai-responses-proxy convert orchestration and record only necessary glue in their convergence Changes, held by session 82cb0265.
