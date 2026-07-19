from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED_OR_LOCAL_ROOTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
}


def test_ci_quality_stage_invokes_config_and_shell_owner_scripts() -> None:
    ci = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "ethos:config:" in ci
    assert "ethos:shell:" in ci
    assert "- tools/ci/scripts/run-config-lint.sh" in ci
    assert "- tools/ci/scripts/run-shell-lint.sh" in ci
    assert "taplo" not in ci
    assert "yamllint" not in ci
    assert "shellcheck" not in ci


def test_config_quality_has_dedicated_policy_not_pyproject_dumping_ground() -> None:
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    config_readme = (ROOT / ".config" / "README.md").read_text(encoding="utf-8")

    assert "[tool.ruff" not in pyproject_text
    assert "[tool.pytest" not in pyproject_text
    assert "[tool.coverage" not in pyproject_text
    assert "[tool.taplo" not in pyproject_text
    assert "strict-config" not in pyproject_text
    assert "select =" not in pyproject_text
    assert ".config/checks/taplo/taplo.toml" in config_readme
    assert ".config/checks/yaml/yamllint.yaml" in config_readme
    assert ".config/checks/whitespace/policy.toml" not in config_readme
    assert ".config/checks/shell/.shellcheckrc" in config_readme
    assert "cache routing" in config_readme
    assert "pyproject.toml` is not a pytest policy" in config_readme


def test_blank_line_owners_use_native_policies_without_custom_reader() -> None:
    markdown = (ROOT / ".config/checks/markdown/.markdownlint-cli2.yaml").read_text(
        encoding="utf-8"
    )
    yaml = (ROOT / ".config/checks/yaml/yamllint.yaml").read_text(encoding="utf-8")
    config_runner = (ROOT / "tools/ci/scripts/run-config-lint.sh").read_text(encoding="utf-8")
    shell_runner = (ROOT / "tools/ci/scripts/run-shell-lint.sh").read_text(encoding="utf-8")

    assert "MD012: {maximum: 1}" in markdown
    assert "empty-lines:" in yaml
    assert "max-start: 0" in yaml
    assert "max-end: 0" in yaml
    markdown_runner = (ROOT / "tools/ci/scripts/run-markdown-lint.sh").read_text(encoding="utf-8")
    assert "ethos_python" in config_runner
    assert "structural_whitespace.py" not in config_runner
    assert "structural_whitespace.py" not in shell_runner
    assert "structural_whitespace.py" not in markdown_runner
    assert not (ROOT / "tools/ci/structural_whitespace.py").exists()
    assert not (ROOT / ".config/checks/whitespace/policy.toml").exists()


def test_toml_files_have_exactly_one_final_newline_and_no_trailing_space() -> None:
    bad: list[str] = []
    for path in sorted(ROOT.rglob("*.toml")):
        if any(part in GENERATED_OR_LOCAL_ROOTS for part in path.relative_to(ROOT).parts):
            continue
        data = path.read_bytes()
        if data and not data.endswith(b"\n"):
            bad.append(f"{path.relative_to(ROOT)}:missing-final-newline")
        if data.endswith(b"\n\n"):
            bad.append(f"{path.relative_to(ROOT)}:extra-trailing-newline")
        for index, line in enumerate(data.splitlines(), start=1):
            if line.rstrip(b" \t") != line:
                bad.append(f"{path.relative_to(ROOT)}:{index}:trailing-space")

    assert bad == []


def test_pytest_runtime_cache_stays_out_of_config_plane() -> None:
    pytest_ini = (ROOT / ".config/checks/pytest/pytest.ini").read_text(encoding="utf-8")
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert not (ROOT / "pytest.ini").exists()
    assert not (ROOT / "ruff.toml").exists()
    assert "cache_dir = build/runtime/tool-cache/pytest" in pytest_ini
    assert "[tool.pytest" not in pyproject_text
    assert "cache_dir = .config/checks/pytest" not in pytest_ini
    assert not (ROOT / ".config" / "checks" / "pytest" / ".gitignore").exists()


def test_tool_catalog_marks_config_gates_active_with_owner_scripts() -> None:
    tools = (ROOT / "system" / "tools.toml").read_text(encoding="utf-8")

    assert re.search(
        r'concern = "toml"[\s\S]*?config = "\.config/checks/taplo/taplo\.toml"[\s\S]*?gate = "tools/ci/scripts/run-config-lint\.sh"',
        tools,
    )
    assert re.search(
        r'concern = "yaml"[\s\S]*?config = "\.config/checks/yaml/yamllint\.yaml"[\s\S]*?gate = "tools/ci/scripts/run-config-lint\.sh"',
        tools,
    )
    assert re.search(
        r'concern = "shell"[\s\S]*?config = "\.config/checks/shell/\.shellcheckrc"[\s\S]*?gate = "tools/ci/scripts/run-shell-lint\.sh"',
        tools,
    )


def test_ruff_runtime_cache_stays_under_build_runtime() -> None:
    runner = (ROOT / "tools/ci/scripts/run-python-lint.sh").read_text(encoding="utf-8")
    ruff_config = (ROOT / ".config/checks/ruff/ruff.toml").read_text(encoding="utf-8")
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    # The root discovery adapter owns only cache routing; it delegates every
    # lint policy decision to the single configuration authority under `.config`.
    assert "build/runtime/tool-cache/ruff" in runner
    assert "--cache-dir" in runner
    assert ".ruff_cache" not in runner
    assert 'cache-dir = "build/runtime/tool-cache/ruff"' in ruff_config
    assert (ROOT / "ruff.toml").is_symlink()
    assert (ROOT / "ruff.toml").readlink().as_posix() == ".config/checks/ruff/ruff.toml"
    settings = subprocess.run(
        [
            "uv",
            "run",
            "--group",
            "dev",
            "ruff",
            "check",
            "--show-settings",
            "packages/ethos/src/ethos/__init__.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    expected_cache_dir = ROOT / "build/runtime/tool-cache/ruff"
    assert f'cache_dir = "{expected_cache_dir}"' in settings
    explicit_settings = subprocess.run(
        [
            "uv",
            "run",
            "--group",
            "dev",
            "ruff",
            "check",
            "--config",
            ".config/checks/ruff/ruff.toml",
            "--show-settings",
            "packages/ethos/src/ethos/__init__.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    assert f'cache_dir = "{expected_cache_dir}"' in explicit_settings
    assert "[tool.ruff" not in pyproject_text


def test_python_lint_owner_supports_macos_bash(tmp_path: Path) -> None:
    """Keep owner scripts portable to the macOS-provided Bash 3.2."""
    repo = tmp_path / "repo"
    scripts = repo / "tools" / "ci" / "scripts"
    scripts.mkdir(parents=True)
    (repo / ".config" / "checks" / "ruff").mkdir(parents=True)
    (repo / ".config" / "checks" / "ruff" / "ruff.toml").write_text(
        "",
        encoding="utf-8",
    )
    (repo / "example.py").write_text("pass\n", encoding="utf-8")

    runner = scripts / "run-python-lint.sh"
    runner.write_text(
        (ROOT / "tools/ci/scripts/run-python-lint.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    runner.chmod(runner.stat().st_mode | stat.S_IXUSR)
    ratchet = scripts / "run-ruff-ratchet.sh"
    ratchet.write_text(
        "#!/bin/sh\nexit 0\n",
        encoding="utf-8",
    )
    ratchet.chmod(ratchet.stat().st_mode | stat.S_IXUSR)

    bin_dir = repo / "bin"
    bin_dir.mkdir()
    git = bin_dir / "git"
    git.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "rev-parse" ]; then printf "%s\\n" "$PWD"; exit 0; fi\n'
        'if [ "$1" = "ls-files" ]; then printf "%s\\0" "example.py"; exit 0; fi\n'
        "exit 1\n",
        encoding="utf-8",
    )
    git.chmod(git.stat().st_mode | stat.S_IXUSR)
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        "shift\n"
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in --group) shift 2 ;; --*) shift ;; *) break ;; esac\n'
        "done\n"
        'exec "$@"\n',
        encoding="utf-8",
    )
    uv.chmod(uv.stat().st_mode | stat.S_IXUSR)
    ruff = bin_dir / "ruff"
    ruff.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ruff.chmod(ruff.stat().st_mode | stat.S_IXUSR)

    env = os.environ | {
        "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    completed = subprocess.run(
        ["/bin/bash", str(runner)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    for owner in (
        ROOT / "tools/ci/scripts/run-python-lint.sh",
        ROOT / "tools/ci/scripts/run-ruff-ratchet.sh",
        ROOT / "tools/ci/scripts/run-bandit.sh",
    ):
        owner_text = owner.read_text(encoding="utf-8")
        assert "mapfile" not in owner_text
        assert 'while IFS= read -r -d "" path' in owner_text
    assert completed.returncode == 0, completed.stderr


def test_python_runtime_wrapper_keeps_macos_bash_compatibility() -> None:
    wrapper = (ROOT / "tools/ci/scripts/with-python-runtime.sh").read_text(encoding="utf-8")

    assert "BASH_VERSINFO" not in wrapper


def test_ty_policy_is_zero_tolerance_without_ratchet_residue() -> None:
    policy_text = (ROOT / ".config/checks/ty/policy.toml").read_text(encoding="utf-8")
    policy = tomllib.loads(policy_text)

    assert policy == {
        "zero_tolerance": {
            "packages": ["packages/ethos-core", "packages/ethos"],
        }
    }
    assert "ratchet" not in policy_text
    assert "baseline" not in policy_text


def test_type_policy_projections_are_zero_tolerance_only() -> None:
    command_help = (ROOT / "system/commands.toml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    template = (ROOT / ".config/ci/templates/hosted/gitlab-ci.yml").read_text(encoding="utf-8")

    assert "zero diagnostics for every package" in command_help
    for projection in (gitlab, template):
        assert "requires zero diagnostics for every declared package" in projection


def test_ruff_ratchet_has_no_zero_debt_ignore_residue() -> None:
    ratchet = tomllib.loads(
        (ROOT / ".config/checks/ruff/ratchet.toml").read_text(encoding="utf-8")
    )["ignored_rule_baseline"]
    ruff_config = (ROOT / ".config/checks/ruff/ruff.toml").read_text(encoding="utf-8")

    zero_baselines = sorted(rule for rule, count in ratchet.items() if count == 0)

    assert zero_baselines == []
    assert '"FBT001"' not in ruff_config
    assert "FBT001 = 0" not in (ROOT / ".config/checks/ruff/ratchet.toml").read_text(
        encoding="utf-8"
    )


def test_ruff_ratchet_uses_tracked_python_file_set() -> None:
    runner = (ROOT / "tools/ci/scripts/run-ruff-ratchet.sh").read_text(encoding="utf-8")

    assert 'git ls-files -z "*.py" "*.pyi"' in runner
    assert '"${python_quality_paths[@]}"' in runner
    assert "mapfile" not in runner
    assert 'while IFS= read -r -d "" path' in runner
    assert '"."' not in runner


def test_ruff_ratchet_rejects_stale_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".config/checks/ruff").mkdir(parents=True)
    (repo / "tools/ci/scripts").mkdir(parents=True)
    (repo / ".config/checks/ruff/ratchet.toml").write_text(
        "[ignored_rule_baseline]\nARG001 = 2\n",
        encoding="utf-8",
    )
    (repo / ".config/checks/ruff/ruff.toml").write_text("", encoding="utf-8")
    (repo / "example.py").write_text("print('tracked')\n", encoding="utf-8")

    runner = repo / "tools/ci/scripts/run-ruff-ratchet.sh"
    runner.write_text(
        (ROOT / "tools/ci/scripts/run-ruff-ratchet.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    runner.chmod(runner.stat().st_mode | stat.S_IXUSR)
    runtime_wrapper = repo / "tools/ci/scripts/with-python-runtime.sh"
    runtime_wrapper.write_text(
        (ROOT / "tools/ci/scripts/with-python-runtime.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    runtime_wrapper.chmod(runtime_wrapper.stat().st_mode | stat.S_IXUSR)

    bin_dir = repo / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "shift  # run\n"
        'while [[ "$1" == --* || "$1" == "--group" ]]; do\n'
        '  if [ "$1" = "--group" ]; then shift 2; else shift; fi\n'
        "done\n"
        'if [ "$1" = "env" ]; then shift; exec env "$@"; fi\n'
        'if [ "$1" = "python" ]; then shift; exec "$PYTHON_BIN" "$@"; fi\n'
        'exec "$@"\n',
        encoding="utf-8",
    )
    uv.chmod(uv.stat().st_mode | stat.S_IXUSR)
    ruff = bin_dir / "ruff"
    ruff.write_text(
        "#!/usr/bin/env bash\nprintf '1 ARG001\\n'\n",
        encoding="utf-8",
    )
    ruff.chmod(ruff.stat().st_mode | stat.S_IXUSR)

    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "add", "example.py"], cwd=repo, check=True)
    env = os.environ | {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTHON_BIN": sys.executable,
    }

    completed = subprocess.run(
        [str(runner)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "ruff ratchet baseline stale: ARG001 1<2" in completed.stderr
    assert "shrink .config/checks/ruff/ratchet.toml" in completed.stderr


def test_ruff_ratchet_uses_semantic_cache_home() -> None:
    runner = (ROOT / "tools/ci/scripts/run-ruff-ratchet.sh").read_text(encoding="utf-8")

    assert "build/runtime/tool-cache/ruff" in runner
    assert "RUFF_CACHE_DIR" in runner
    assert ".ruff_cache" not in runner
