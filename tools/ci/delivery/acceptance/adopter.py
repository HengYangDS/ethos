"""Signed adopted-repository fixture for package delivery proof."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.openspec.cli import archive_result
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.openspec.cli import run_json
from ethos.adapters.process import run_command
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from tools.ci.delivery.acceptance.first_change import prove_first_change
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Mapping

CommandRunner = Callable[..., str]


def _required_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        message = f"required executable is unavailable: {name}"
        raise RuntimeError(message)
    return executable


def _configure_product_signer(root: Path, *, git: str, run: CommandRunner) -> None:
    ssh_keygen = _required_executable("ssh-keygen")
    signer = root.parent / "product-signer"
    trust_root = root.parent / "trust"
    trust_root.mkdir(mode=0o700)
    trust_anchor = trust_root / "allowed-signers"
    run(ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-f", str(signer))
    public_key = signer.with_suffix(".pub").read_text(encoding="utf-8").strip()
    trust_anchor.write_text(
        f'ethos-install-smoke@example.invalid namespaces="git" {public_key}\n',
        encoding="utf-8",
    )
    protect_for_current_identity(trust_root)
    protect_for_current_identity(trust_anchor)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", ssh_keygen),
        ("gpg.ssh.allowedSignersFile", str(trust_anchor)),
        ("user.signingkey", str(signer.with_suffix(".pub"))),
        ("commit.gpgsign", "true"),
    ):
        run(git, "config", name, value, cwd=root)


def materialize_bootstrap_repository(root: Path, *, run: CommandRunner) -> None:
    """Create the minimal Git root required for first runtime activation."""
    root.mkdir()
    run(_required_executable("git"), "init", "--quiet", "--initial-branch=dev", str(root))


def materialize_adopter(
    root: Path,
    *,
    openspec_config: Path,
    run: CommandRunner,
) -> str:
    """Materialize and commit one signed repository adopted by the installed wheel."""
    git = _required_executable("git")
    run(git, "init", "--quiet", "--initial-branch=dev", str(root))
    run(git, "config", "user.name", "ETHOS Install Smoke", cwd=root)
    run(git, "config", "user.email", "ethos-install-smoke@example.invalid", cwd=root)
    _configure_product_signer(root, git=git, run=run)
    (root / ".ethos").mkdir()
    change = root / "openspec/changes/smoke-change"
    change.mkdir(parents=True)
    (root / ".ethos/profile.toml").write_text(
        'profile_id = "installed-cli-adopter"\n\n[openspec]\nmaterial_paths = ["**"]\n',
        encoding="utf-8",
    )
    (root / ".ethos/release.toml").write_text(
        """[publication]
local_verification_command = "git fsck --no-reflogs"
local_installation_command = "git --version"

[[publication.peers]]
id = "file"
provider = "git"
role = "package_smoke"
git_remote = "origin"
capabilities = ["repository", "publication"]
""",
        encoding="utf-8",
    )
    (root / ".gitattributes").write_text(
        "* text=auto eol=lf\nline-ending-*.txt -text\n",
        encoding="utf-8",
    )
    shutil.copy2(openspec_config, root / "openspec/config.yaml")
    (change / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    (change / "proposal.md").write_text(
        "## Why\n\nExercise the installed package lifecycle.\n\n"
        "## What Changes\n\n- Add one package-smoke change.\n\n"
        "## Out of Scope\n\n- Product behavior.\n",
        encoding="utf-8",
    )
    (change / "design.md").write_text(
        "## Context\n\nPackage-only lifecycle proof.\n\n"
        "## Decision\n\nUse only official OpenSpec artifacts.\n",
        encoding="utf-8",
    )
    (change / "tasks.md").write_text(
        "## 1. Package smoke\n\n- [x] 1.1 Exercise installed lifecycle.\n",
        encoding="utf-8",
    )
    spec = change / "specs/package-smoke/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "## Purpose\n\n"
        "Verify installed governance of native repository changes without source access.\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: Installed lifecycle\n\n"
        "The installed package SHALL govern an official OpenSpec Change.\n\n"
        "#### Scenario: Package smoke runs\n\n"
        "- **WHEN** the installed lifecycle executes\n"
        "- **THEN** no parallel intent carrier is required\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# installed CLI adopter\n", encoding="utf-8")
    peer = root.parent / "publication-peer.git"
    run(git, "init", "--quiet", "--bare", str(peer))
    run(git, "remote", "add", "origin", str(peer), cwd=root)
    run(git, "add", ".", cwd=root)
    run(git, "commit", "--quiet", "-m", "initialize installed CLI adopter", cwd=root)
    return run(git, "rev-parse", "HEAD", cwd=root)


def verify_formed(
    target: Path,
    plan: dict[str, object],
    applied: dict[str, object],
    observation: tuple[int, dict[str, object], str],
    expected_guidance: str,
) -> str:
    """Reobserve exact Git, installed guidance and every formed output."""
    code, status, _detail = observation
    data = status.get("data")
    effect = applied.get("effect")
    if (
        code
        or status.get("verdict") != "pass"
        or not isinstance(data, dict)
        or not isinstance(data.get("head"), str)
        or not isinstance(effect, dict)
        or data.get("head") != effect.get("head")
        or data.get("dirty") is not False
        or not isinstance(data.get("hook_runtime"), dict)
        or data["hook_runtime"].get("current") is not True
    ):
        message = (
            f"installed_formation_status_invalid:exit={code}:"
            f"gaps={status.get('required_gaps')}:"
            f"head={data.get('head') if isinstance(data, dict) else None}:effect={effect}"
        )
        raise RuntimeError(message)
    context = status.get("governance_context")
    guidance = context.get("agent_guidance") if isinstance(context, dict) else None
    entry = target / "AGENTS.md"
    if (
        not isinstance(guidance, dict)
        or guidance.get("sha256") != expected_guidance
        or not isinstance(guidance.get("path"), str)
        or not Path(guidance["path"]).is_file()
        or hashlib.sha256(Path(guidance["path"]).read_bytes()).hexdigest() != expected_guidance
        or not entry.is_file()
        or "ethos status --root . --json" not in entry.read_text(encoding="utf-8")
    ):
        message = "installed_formation_guidance_invalid"
        raise RuntimeError(message)
    outputs = plan.get("write_plan")
    if not isinstance(outputs, list):
        message = "installed_formation_output_invalid"
        raise TypeError(message)
    for output in outputs:
        if not isinstance(output, dict) or not isinstance(output.get("path"), str):
            message = "installed_formation_output_invalid"
            raise TypeError(message)
        relative = Path(output["path"])
        if (
            not relative.parts
            or relative.is_absolute()
            or ".." in relative.parts
            or hashlib.sha256((target / relative).read_bytes()).hexdigest()
            != output.get("content_sha256")
        ):
            message = "installed_formation_output_invalid"
            raise RuntimeError(message)
    return str(data["head"])


def _verify_candidate(
    target: Path, applied: dict[str, object], head: str, environment: Mapping[str, str]
) -> None:
    """Read both Git coordinates independently of the formation result."""
    effect = applied.get("effect")
    path = effect.get("candidate_worktree_path") if isinstance(effect, dict) else None
    if not isinstance(path, str):
        message = "installed_formation_candidate_invalid"
        raise TypeError(message)
    candidate = Path(path)
    if not candidate.is_dir() or candidate.is_symlink():
        message = "installed_formation_candidate_invalid"
        raise RuntimeError(message)
    for root, revision in ((target, "candidate/dev"), (candidate, "HEAD")):
        observed = run_command(
            root,
            ("git", "rev-parse", revision),
            env=environment,
            inherit_environment=False,
            check=False,
        )
        if observed.returncode or observed.stdout.strip() != head:
            message = "installed_formation_candidate_invalid"
            raise RuntimeError(message)


def prove_formation(
    executable: Path,
    work: Path,
    *,
    origin: str,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Form both starters from the installed CLI without a source checkout."""
    package_guidance = (
        Path(origin).parent / "data/skills/ethos-repository-work/SKILL.md"
    ).read_bytes()
    expected_guidance = hashlib.sha256(package_guidance).hexdigest()
    formed: list[dict[str, object]] = []
    journey = {"first_change": "not_attempted", "agent_handoff": "not_attempted"}
    for starter in ("foundation", "python-library"):
        target = work / f"formed-{starter}"
        command = (
            str(executable),
            "adopt",
            "--create",
            "--root",
            str(target),
            "--starter",
            starter,
            "--purpose",
            "An independently installed governed repository.",
            "--author-name",
            "ETHOS Install Smoke",
            "--author-email",
            "ethos-install-smoke@example.invalid",
        )
        preview_code, preview, preview_detail = invoke(
            work, (*command, "--json"), environment=environment
        )
        plan = preview.get("data")
        if (
            preview_code
            or preview.get("verdict") != "pass"
            or not isinstance(plan, dict)
            or target.exists()
        ):
            message = (
                f"installed_formation_preview_failed:exit={preview_code}:"
                f"gaps={preview.get('required_gaps')}:detail={preview_detail[-256:]}"
            )
            raise RuntimeError(message)
        digest = plan.get("plan_digest")
        candidate = plan.get("candidate_worktree_path")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or not isinstance(candidate, str)
            or Path(candidate).exists()
        ):
            message = "installed_formation_plan_invalid"
            raise RuntimeError(message)
        apply_command = (
            *command,
            "--apply",
            "--authorize",
            "--expect-plan-digest",
            digest,
            "--json",
        )
        applied_code, applied, applied_detail = invoke(work, apply_command, environment=environment)
        applied_data = applied.get("data")
        if (
            applied_code
            or applied.get("verdict") != "pass"
            or not isinstance(applied_data, dict)
            or applied_data.get("applied") is not True
            or not target.is_dir()
        ):
            message = (
                f"installed_formation_apply_failed:exit={applied_code}:"
                f"gaps={applied.get('required_gaps')}:detail={applied_detail[-256:]}"
            )
            raise RuntimeError(message)
        status_command = (str(executable), "status", "--root", str(target), "--json")
        head = verify_formed(
            target,
            plan,
            applied_data,
            invoke(target, status_command, environment=environment),
            expected_guidance,
        )
        _verify_candidate(target, applied_data, head, environment)
        retry_code, retry, _retry_detail = invoke(work, apply_command, environment=environment)
        if retry_code == 0 or retry.get("required_gaps") != ["formation_target_exists"]:
            message = "installed_formation_retry_replayed_effect"
            raise RuntimeError(message)
        preserved = invoke(target, status_command, environment=environment)
        verify_formed(
            target,
            plan,
            applied_data,
            preserved,
            expected_guidance,
        )
        if starter == "foundation":
            journey = prove_first_change(
                executable,
                target,
                environment=environment,
            )
        if starter == "python-library":
            evolved_code, evolved, evolved_detail = invoke(
                target,
                (
                    str(executable),
                    "adopt",
                    "--evolve-starter",
                    "--root",
                    str(target),
                    "--purpose",
                    "A revised independently installed repository.",
                    "--json",
                ),
                environment=environment,
            )
            if evolved_code or evolved.get("verdict") != "pass":
                evolved_data = evolved.get("data")
                failure = (
                    evolved_data.get("detail") if isinstance(evolved_data, dict) else None
                ) or evolved_detail[-256:]
                message = (
                    f"installed_starter_evolution_preview_failed:exit={evolved_code}:"
                    f"gaps={evolved.get('required_gaps')}:detail={failure}"
                )
                raise RuntimeError(message)
        formed.append({"starter": starter, "head": head})
    return {
        "state": "passed",
        "formed": formed,
        "guidance_sha256": expected_guidance,
        **journey,
        "retry_preserved": True,
        "source_checkout_required": False,
    }


def line_ending_conformance(adopter: Path, *, run: CommandRunner) -> list[str]:
    """Round-trip LF, CRLF, and UTF-8 through Git without text-mode inference."""
    git = _required_executable("git")
    fixtures = {
        "lf": b"portable UTF-8: \xe9\x81\x93\n",
        "crlf": b"portable UTF-8: \xe9\x81\x93\r\n",
    }
    observed: list[str] = []
    for style, payload in fixtures.items():
        relative = f"line-ending-{style}.txt"
        path = adopter / relative
        path.write_bytes(payload)
        run(git, "add", "--", relative, cwd=adopter)
        git_blob = run_command(
            adopter,
            (git, "show", f":{relative}"),
            text=False,
            check=True,
            remove_env_prefixes=("GIT_",),
        ).stdout
        if git_blob != payload or path.read_bytes() != payload:
            message = f"portable line-ending round-trip failed: {style}"
            raise RuntimeError(message)
        observed.append(style)
    run(git, "reset", "--quiet", "--", *[f"line-ending-{s}.txt" for s in observed], cwd=adopter)
    for style in observed:
        (adopter / f"line-ending-{style}.txt").unlink()
    return observed


def prepare_acceptance_topology(
    root: Path,
    *,
    run: CommandRunner,
) -> Path:
    """Prepare the repository facts consumed by one package-acceptance run."""
    git = _required_executable("git")
    openspec = openspec_base_command()
    if openspec is None:
        message = "package_acceptance_openspec_unavailable"
        raise RuntimeError(message)
    archived = run_json(root, openspec, ("archive", "smoke-change", "--yes", "--json"), timeout=20)
    if archive_result(root, "smoke-change", archived)[0]:
        message = f"package_acceptance_openspec_archive_failed:{archived}"
        raise RuntimeError(message)
    run(git, "add", "--all", "--", "openspec", cwd=root)
    run(git, "commit", "--quiet", "-m", "complete package smoke change", cwd=root)
    candidate = root.parent / "repo-candidate-dev"
    run(git, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev", cwd=root)
    (root / "accepted.txt").write_text("accepted\n", encoding="utf-8")
    run(git, "add", "accepted.txt", cwd=root)
    run(git, "commit", "--quiet", "-m", "advance accepted independently", cwd=root)
    (candidate / "candidate.txt").write_text("candidate\n", encoding="utf-8")
    run(git, "add", "candidate.txt", cwd=candidate)
    run(git, "commit", "--quiet", "-m", "advance candidate independently", cwd=candidate)
    (root / ".ethos/workspace.toml").write_text(
        '[branch_roles]\nrelease_branch = "main"\naccepted_branch = "dev"\n'
        'candidate_branch = "candidate/dev"\nrelease_mirror = "independent"\n'
        'work_branch_prefix = "work/"\nproposal_branch_prefix = "proposal/"\n'
        "canonical_sibling_worktrees = false\n"
        '[commit_policy]\nsubject_pattern = ".+"\nsigning_required = true\n'
        'signing_format = "ssh"\n',
        encoding="utf-8",
    )
    profile = root / ".ethos/profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8") + '\n[proof]\ngate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )
    registry = root / "system/gates.toml"
    registry.parent.mkdir()
    registry.write_text(
        'schema_version = 1\nid = "package-smoke-trust"\n\n'
        '[proof_sets]\ndefault = ["signature-trust", "patch-validity"]\n'
        'full = ["signature-trust", "patch-validity"]\n\n'
        '[[gates]]\nid = "signature-trust"\nkind = "governance"\n'
        'command = ["git", "verify-commit", "HEAD"]\n'
        'profile = "repository"\ntoolchain = "git"\n'
        'asset_classes = ["git-history"]\ndimensions = ["signature-trust"]\n'
        'execution_mode = "subprocess"\nevidence_class = "contract"\n'
        'trust_bearing = true\ntool_adapter = "repository-native"\n'
        'version_source = "git"\n\n'
        '[[gates]]\nid = "patch-validity"\nkind = "governance"\n'
        'command = ["git", "diff", "--check", "HEAD^", "HEAD"]\n'
        'profile = "repository"\ntoolchain = "git"\n'
        'asset_classes = ["git-history"]\ndimensions = ["patch-integrity"]\n'
        'execution_mode = "subprocess"\nevidence_class = "contract"\n'
        'trust_bearing = true\ntool_adapter = "repository-native"\n'
        'version_source = "git"\n',
        encoding="utf-8",
    )
    run(git, "add", ".ethos/workspace.toml", ".ethos/profile.toml", "system/gates.toml", cwd=root)
    run(
        git,
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "-m",
        "require accepted signature repair",
        cwd=root,
    )
    return candidate
