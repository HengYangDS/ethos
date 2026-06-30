from __future__ import annotations

import json
from pathlib import Path

PROFILES = ("generic", "python-package", "monorepo", "github", "gitlab")

STATIC_DEFAULT_FILES = {
    ".ethos/rules.toml": """[command_plane]\npublic = \"ethos\"\n""",
    ".ethos/assistants.toml": """[projections]\ntruth = \"repository\"\n""",
    ".ethos/state/.gitignore": "*\n!.gitignore\n",
}


def available_profiles() -> tuple[str, ...]:
    return PROFILES


def _workspace_toml(root: Path, profile: str) -> str:
    packages_dir = root / "packages"
    if profile == "monorepo" and packages_dir.exists():
        blocks = []
        for package in sorted(path for path in packages_dir.iterdir() if path.is_dir()):
            blocks.append(
                f'[[package]]\nname = "{package.name}"\n'
                f'path = "packages/{package.name}"\ndomains = ["package"]\n'
            )
        if blocks:
            return "\n".join(blocks)
    return '[[package]]\nname = "root"\npath = "."\ndomains = ["repository"]\n'


def _gitlab_ci() -> str:
    return (
        "stages:\n"
        "  - verify\n\n"
        "ethos:verify:\n"
        "  stage: verify\n"
        "  image: python:3.12\n"
        "  script:\n"
        "    - pip install uv\n"
        "    - uv run --group dev pytest tests/unit tests/architecture -q\n"
        "    - uv run --group dev ruff check .\n"
        "    - uv run --package ethos ethos self audit --json\n"
        "    - uv run --package ethos ethos report --json\n"
    )


def _default_files(root: Path, profile: str) -> dict[str, str]:
    project_name = json.dumps(root.name)
    files = {
        ".ethos/project.toml": (
            f"[meta]\nname = {project_name}\nproduct = \"ETHOS\"\nversion = 1\n"
        ),
        ".ethos/workspace.toml": _workspace_toml(root, profile),
        **STATIC_DEFAULT_FILES,
    }
    if profile == "gitlab":
        files[".gitlab-ci.yml"] = _gitlab_ci()
    if profile == "github":
        files[".github/workflows/ethos.yml"] = (
            "name: ethos\non: [push, pull_request]\njobs:\n"
            "  verify:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n      - uses: astral-sh/setup-uv@v5\n"
            "      - run: uv run --group dev pytest tests/unit tests/architecture -q\n"
            "      - run: uv run --package ethos ethos report --json\n"
        )
    return files


def detect_repo_profile(root: Path) -> str:
    if (root / "pyproject.toml").exists():
        return "python-package"
    if (root / ".gitlab-ci.yml").exists():
        return "gitlab"
    if (root / ".github").exists():
        return "github"
    return "generic"


def adoption_plan(
    root: Path,
    *,
    profile: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    selected_profile = profile or detect_repo_profile(root)
    if selected_profile not in PROFILES:
        msg = f"unknown ETHOS adoption profile: {selected_profile}"
        raise ValueError(msg)
    files = _default_files(root, selected_profile)
    planned = sorted(files)
    if apply:
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    return {
        "root": str(root),
        "planned_files": planned,
        "applied": apply,
        "profile": selected_profile,
        "available_profiles": list(PROFILES),
    }
