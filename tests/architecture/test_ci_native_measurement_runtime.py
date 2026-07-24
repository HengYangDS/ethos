from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_RUNTIME = "3.14"


def test_hosted_ci_uses_the_native_measurement_runtime() -> None:
    github = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    gitlab = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))

    def setup_python_version(job: str) -> str:
        step = next(
            step
            for step in github["jobs"][job]["steps"]
            if step.get("uses") == "actions/setup-python@v6"
        )
        return step["with"]["python-version"]

    assert [setup_python_version(job) for job in ("quality", "verify", "package")] == [
        CANONICAL_RUNTIME
    ] * 3
    assert gitlab[".python_setup"]["image"] == f"python:{CANONICAL_RUNTIME}"
    assert gitlab["ethos:npm"]["image"] == f"python:{CANONICAL_RUNTIME}"
    assert gitlab["ethos:npm-package"]["image"] == f"python:{CANONICAL_RUNTIME}"


def test_gitlab_verify_runs_native_measurement_under_unprivileged_identity() -> None:
    gitlab = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    variables = gitlab["ethos:verify"]["variables"]

    assert variables["ETHOS_TEST_WORKERS"] == "1"
    assert variables["ETHOS_TEST_RUN_AS_UID"] == "65534"
    assert variables["ETHOS_TEST_RUN_AS_GID"] == "65534"
    assert "ETHOS_TEST_RUN_AS_UID" not in gitlab["variables"]
    assert "ETHOS_TEST_RUN_AS_GID" not in gitlab["variables"]


def test_hosted_bootstrap_keeps_the_openspec_shim_in_its_job_local_venv() -> None:
    bootstrap = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")

    assert 'bootstrap_python="${ETHOS_BOOTSTRAP_PYTHON:-python3}"' in bootstrap
    assert '"${bootstrap_python}" -m venv "${bootstrap_venv}"' in bootstrap
    assert 'openspec_shim="${bootstrap_venv}/bin/openspec"' in bootstrap
    assert ' > "${openspec_shim}"' in bootstrap
    assert 'printf \'%s\\n\' "${bootstrap_venv}/bin" >> "${GITHUB_PATH}"' in bootstrap
    assert 'exec npx --yes @fission-ai/openspec@1.6.0 "$@"' in bootstrap
    assert ')/install-node.sh"' in bootstrap
    assert "apt-get" not in bootstrap
    assert "/usr/local/bin/openspec" not in bootstrap
