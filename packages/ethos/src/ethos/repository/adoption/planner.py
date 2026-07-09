from __future__ import annotations

import hashlib
from pathlib import Path

from ethos.repository.adoption.scaffold.core import BASE_ADOPTION_FILES
from ethos.repository.adoption.scaffold.core import OPENSPEC_CAPABILITIES
from ethos.repository.adoption.scaffold.core import default_files

PROFILES = ("generic", "python", "monorepo", "github", "gitlab")
PROFILE_READ_FILES = {
    "generic": (".git", ".gitignore", "README.md"),
    "python": ("pyproject.toml", "uv.lock", "noxfile.py", "pytest.ini", "ruff.toml"),
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


def _write_plan(root: Path, files: dict[str, str]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for relative in sorted(files):
        content = files[relative]
        target = root / relative
        existed = target.exists()
        conflict = False
        if not existed:
            action = "create"
        else:
            existing = target.read_text(encoding="utf-8")
            if existing == content:
                action = "keep_existing"
            elif existing == "":
                action = "write_empty"
            else:
                action = "skip_existing_nonempty"
                conflict = True
        plan.append(
            {
                "path": relative,
                "action": action,
                "conflict": conflict,
                "existed": existed,
                "content_sha256": _sha256_text(content),
                "preview": content.splitlines()[0] if content.splitlines() else "",
            }
        )
    return plan


def adoption_plan(
    root: Path,
    *,
    profile: str | None = None,
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
    write_plan = _write_plan(root, files)
    conflict_gaps = [f"adoption_conflict:{item['path']}" for item in write_plan if item["conflict"]]
    profile_ok = bool(profile_match["ok"])
    required_gaps = list(conflict_gaps)
    if apply and not profile_ok:
        required_gaps.append(f"profile_mismatch:{selected_profile}")
    generated_files = sorted(str(item["path"]) for item in write_plan if not bool(item["existed"]))
    applied = bool(apply and not required_gaps)
    if applied:
        for relative, content in files.items():
            item = next(entry for entry in write_plan if entry["path"] == relative)
            if item["action"] == "keep_existing":
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
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
        "detected_profile": detected_profile,
        "profile_match": profile_match,
        "requested_profile": requested_profile,
        "profile_aliases": [],
        "available_profiles": list(PROFILES),
        "existing_files": existing,
        "write_plan": write_plan,
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
