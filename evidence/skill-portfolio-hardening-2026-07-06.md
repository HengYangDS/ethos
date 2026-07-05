# Evidence: skill-portfolio-hardening

Scope: harden ETHOS repo-local skill portfolio checks without adding a new skill
or truth store.

Commands captured during implementation:

```text
uv run --group dev ruff check packages/ethos/src/ethos/assistants/skill_packages.py packages/ethos/src/ethos/assistants/playbooks.py tests/unit/assistants/test_skill_packages.py tests/unit/assistants/test_playbooks.py
# All checks passed.

uv run --group dev pytest tests/unit/assistants/test_skill_packages.py tests/unit/assistants/test_playbooks.py -q
# 14 passed

ETHOS_ROOT=$PWD uv run --group dev ethos playbooks check --mode v2-strict --json
# ok=true, required_gaps=[]

ETHOS_ROOT=$PWD uv run --group dev ethos quality projection-drift --json
# ok=true, required_gaps=[]
```

Design binding:

- Signaled hidden route overlap through `portfolio_design`.
- Preserved the five-skill MECE portfolio instead of adding a sixth skill.
- Kept skills as digest-bound projections over repository truth.
