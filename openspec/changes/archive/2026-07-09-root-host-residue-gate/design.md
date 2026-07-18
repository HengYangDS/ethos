# Design

The owner remains `tools/ci/scripts/run-repository-hygiene.sh`. The policy moves
from embedded constants into `.config/checks/repository-hygiene/policy.toml` so
quality thresholds, text-file scope, stash-language policy, large-file allowlist,
and root host-residue names share one stable owner.

The gate checks configured host-residue names by direct root-path existence
before relying on `git ls-files`, because global Git ignores can hide these files
from normal status. Entries must be root filenames only; absolute paths or nested
paths fail the policy check.

This is a boundary gate, not a janitor. Reporting residue makes the hidden state
visible and lets a human/agent remove it intentionally. The gate does not delete,
stash, commit, or transform local residue.
