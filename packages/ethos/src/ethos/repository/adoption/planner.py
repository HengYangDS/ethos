from __future__ import annotations

import hashlib
from pathlib import Path

from ethos.repository.adoption.scaffold.core import BASE_ADOPTION_FILES
from ethos.repository.adoption.scaffold.core import OPENSPEC_CAPABILITIES
from ethos.repository.adoption.scaffold.core import default_files

PROFILES = ("generic", "python", "monorepo", "github", "gitlab")
PROFILE_READ_FILES = {
    "generic": (".git", ".gitignore", "README.md"),
    "python": (
        "pyproject.toml",
        "uv.lock",
        "noxfile.py",
        ".config/checks/pytest/pytest.ini",
        ".config/checks/ruff/ruff.toml",
    ),
    "monorepo": ("packages", "pyproject.toml", "package.json"),
    "github": (".github/workflows", ".git/config"),
    "gitlab": (".gitlab-ci.yml", ".gitlab", ".git/config"),
}
PROFILE_MATCH_REQUIRED = {
    "generic": (),
    "python": ("pyproject.toml",),
    "monorepo": ("packages",),
    "github": (".github",),
    "gitlab": (".gitlab-ci.yml", ".gitlab"),
}
APPLY_CRITERIA = (
    "profile matches the repository shape",
    "planned_files contains only expected ETHOS governance files",
    "hosted CI and remote publication remain projections until externally proven",
    "rollback path is understood before apply",
)

_OVERLAY_ROOT_FILES = frozenset({"AGENTS.md", "CHANGELOG.md", "CONTRIBUTING.md"})
_OVERLAY_PREFIXES = ("docs/", "openspec/")


def available_profiles() -> tuple[str, ...]:
    return PROFILES


def _canonical_profile(profile: str) -> str:
    return profile


def detect_repo_profile(root: Path) -> str:
    if (root / ".gitlab-ci.yml").exists():
        return "gitlab"
    if (root / ".github").exists():
        return "github"
    if (root / "packages").exists():
        return "monorepo"
    if (root / "pyproject.toml").exists():
        return "python"
    return "generic"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _missing_gitignore_lines(existing: str, desired: str) -> tuple[str, ...]:
    existing_lines = set(existing.splitlines())
    return tuple(line for line in desired.splitlines() if line not in existing_lines)


def _append_gitignore_lines(existing: str, missing_lines: tuple[str, ...]) -> str:
    separator = "" if existing.endswith("\n") else "\n"
    return f"{existing}{separator}\n" + "\n".join(missing_lines) + "\n"


def _observed_files(root: Path, profile: str) -> dict[str, bool]:
    return {relative: (root / relative).exists() for relative in PROFILE_READ_FILES[profile]}


def _profile_match(root: Path, profile: str, detected_profile: str) -> dict[str, object]:
    if profile == "generic":
        return {"ok": True, "reasons": ["matched:generic"]}
    required = PROFILE_MATCH_REQUIRED[profile]
    if profile == detected_profile or any((root / relative).exists() for relative in required):
        return {"ok": True, "reasons": [f"matched:{profile}"]}
    reasons = [f"detected:{detected_profile}"]
    reasons.extend(f"missing:{relative}" for relative in required)
    return {"ok": False, "reasons": reasons}


def _overlay_preserves(relative: str, profile: str) -> bool:
    """Return whether overlay mode preserves this adopter-owned scaffold surface."""
    if relative in _OVERLAY_ROOT_FILES or relative.startswith(_OVERLAY_PREFIXES):
        return True
    if profile == "gitlab" and relative == ".gitlab-ci.yml":
        return True
    return profile == "github" and relative.startswith(".github/")


def _overlay_skips_missing(root: Path, relative: str, profile: str) -> bool:
    """Return whether an existing adopter root owns a missing scaffold child."""
    if relative.startswith("docs/"):
        return (root / "docs").exists()
    if relative.startswith("openspec/"):
        return (root / "openspec").exists()
    if profile == "gitlab" and relative == ".gitlab-ci.yml":
        return True
    return profile == "github" and relative.startswith(".github/")


def _write_plan(
    root: Path,
    files: dict[str, str],
    *,
    profile: str = "generic",
    overlay: bool = False,
) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for relative in sorted(files):
        content = files[relative]
        target = root / relative
        existed = target.exists()
        conflict = False
        existing_sha256 = ""
        if not existed:
            action = (
                "preserve_adopter_root"
                if overlay and _overlay_skips_missing(root, relative, profile)
                else "create"
            )
        else:
            existing = target.read_text(encoding="utf-8")
            existing_sha256 = _sha256_text(existing)
            if existing == content:
                action = "keep_existing"
            elif existing == "":
                action = "write_empty"
            elif relative == ".gitignore":
                missing_lines = _missing_gitignore_lines(existing, content)
                action = "keep_existing" if not missing_lines else "merge_gitignore"
            elif overlay and _overlay_preserves(relative, profile):
                action = "preserve_existing"
            else:
                action = "skip_existing_nonempty"
                conflict = True
        entry: dict[str, object] = {
            "path": relative,
            "action": action,
            "conflict": conflict,
            "existed": existed,
            "content_sha256": _sha256_text(content),
            "preview": content.splitlines()[0] if content.splitlines() else "",
        }
        if overlay:
            entry["existing_sha256"] = existing_sha256
        plan.append(entry)
    return plan


def adoption_plan(
    root: Path,
    *,
    profile: str | None = None,
    overlay: bool = False,
    apply: bool = False,
) -> dict[str, object]:
    requested_profile = profile or detect_repo_profile(root)
    selected_profile = _canonical_profile(requested_profile)
    if selected_profile not in PROFILES:
        msg = f"unknown ETHOS adoption profile: {selected_profile}"
        raise ValueError(msg)
    detected_profile = detect_repo_profile(root)
    observed = _observed_files(root, selected_profile)
    profile_match = _profile_match(root, selected_profile, detected_profile)
    files = default_files(root, selected_profile)
    planned = sorted(files)
    existing = sorted(relative for relative in files if (root / relative).exists())
    write_plan = _write_plan(root, files, profile=selected_profile, overlay=overlay)
    conflict_gaps = [f"adoption_conflict:{item['path']}" for item in write_plan if item["conflict"]]
    profile_ok = bool(profile_match["ok"])
    required_gaps = list(conflict_gaps)
    if apply and not profile_ok:
        required_gaps.append(f"profile_mismatch:{selected_profile}")
    generated_files = sorted(
        str(item["path"]) for item in write_plan if item["action"] in {"create", "write_empty"}
    )
    applied = bool(apply and not required_gaps)
    if applied:
        for relative, content in files.items():
            item = next(entry for entry in write_plan if entry["path"] == relative)
            if item["action"] in {
                "keep_existing",
                "preserve_existing",
                "preserve_adopter_root",
            }:
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if item["action"] == "merge_gitignore":
                existing = target.read_text(encoding="utf-8")
                missing_lines = _missing_gitignore_lines(existing, content)
                target.write_text(
                    _append_gitignore_lines(existing, missing_lines), encoding="utf-8"
                )
            else:
                target.write_text(content, encoding="utf-8")
    if conflict_gaps:
        next_action = "resolve adoption conflicts before apply"
    elif not profile_ok:
        next_action = "review profile mismatch before apply"
    elif applied:
        next_action = "ethos status"
    else:
        next_action = "review dry-run write plan"
    return {
        "root": str(root),
        "planned_files": planned,
        "read_files": list(PROFILE_READ_FILES[selected_profile]),
        "observed_files": observed,
        "applied": applied,
        "profile": selected_profile,
        "mode": "overlay" if overlay else "strict",
        "detected_profile": detected_profile,
        "profile_match": profile_match,
        "requested_profile": requested_profile,
        "profile_aliases": [],
        "available_profiles": list(PROFILES),
        "existing_files": existing,
        "write_plan": write_plan,
        "preserved_files": [
            {"path": item["path"], "sha256": item["existing_sha256"]}
            for item in write_plan
            if item["action"] == "preserve_existing"
        ],
        "skipped_files": [
            str(item["path"]) for item in write_plan if item["action"] == "preserve_adopter_root"
        ],
        "apply_criteria": list(APPLY_CRITERIA),
        "required_gaps": required_gaps,
        "next_action": next_action,
        "rollback": {
            "mode": "remove_generated_files_or_restore_git_state",
            "planned_files": planned,
            "generated_files": generated_files,
        },
    }


def adoption_scaffold_report() -> dict[str, object]:
    required = set(BASE_ADOPTION_FILES)
    required.update(f"openspec/specs/{family}/spec.md" for family in OPENSPEC_CAPABILITIES)
    required.update(f"openspec/specs/{family}/capability.toml" for family in OPENSPEC_CAPABILITIES)
    planned = set(default_files(Path("sample"), "gitlab"))
    missing = sorted(required - planned)
    return {
        "ok": not missing,
        "required_files": sorted(required),
        "missing": missing,
        "profiles": list(PROFILES),
        "openspec_capabilities": list(OPENSPEC_CAPABILITIES),
    }
