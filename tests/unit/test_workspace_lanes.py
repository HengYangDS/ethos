from __future__ import annotations

import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ethos_adapters.lanes import bind_work_lane_claim, retire_landed_work_lanes, start_work_lane
from ethos_adapters.prewrite import prewrite_guard
from ethos_adapters.state import active_leases
from ethos_adapters.status import workspace_status
from ethos_repository.schema_validation import validate_schema_instance


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    return path


def write_role_policy(
    repo: Path,
    *,
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    (repo / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[branch_roles]",
                'release_branch = "main"',
                'accepted_branch = "dev"',
                f'candidate_branch = "{candidate_branch}"',
                f'work_branch_prefix = "{work_branch_prefix}"',
                f'submit_branch_prefix = "{submit_branch_prefix}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configure branch roles",
    )


def assert_no_ui_projection(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"open_action", "open_label", "action", "label"}
        assert not (forbidden & set(value))
        for child in value.values():
            assert_no_ui_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_ui_projection(child)


def test_workspace_status_reports_foreign_work_lanes_without_reading_them(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")

    status = workspace_status(repo)

    assert status["role"] == "accepted_root"
    assert status["foreign_work_lanes"] == [
        {
            "branch": "work/foreign",
            "head": git(repo, "rev-parse", "dev"),
            "path": foreign.as_posix(),
            "role": "work_lane",
            "worktree_binding": "linked",
            "lease_owner": "",
            "lease_state": "missing",
            "claim_id": "",
            "claim_binding": "missing",
        }
    ]
    assert status["required_gaps"] == []
    assert status["coordination_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_missing_lease:work/foreign",
    ]
    assert status["closeout_support"] == {
        "supported": False,
        "branch": "",
        "target_branch": "candidate/dev",
        "target_path": (tmp_path / "repo-candidate-dev").as_posix(),
        "operation": "",
        "owner": "",
        "claim_id": "",
        "claim_binding": "unbound",
        "required_gaps": ["protected_root_mutation"],
    }
    assert_no_ui_projection(status)


def test_workspace_status_reports_branch_worktree_bindings_without_ui_actions(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    submit = tmp_path / "repo-submit-feature"
    git(repo, "worktree", "add", "-b", "submit/feature", submit.as_posix(), "dev")

    status = workspace_status(repo)

    assert "branch_actions" not in status
    assert status["role_policy"] == {
        "release_branch": "main",
        "accepted_branch": "dev",
        "candidate_branch": "candidate/dev",
        "work_branch_prefix": "work/",
        "submit_branch_prefix": "submit/",
        "semantic_order": [
            {
                "role": "release_root",
                "kind": "exact_branch",
                "config_key": "release_branch",
                "pattern": "main",
            },
            {
                "role": "accepted_root",
                "kind": "exact_branch",
                "config_key": "accepted_branch",
                "pattern": "dev",
            },
            {
                "role": "candidate",
                "kind": "exact_branch",
                "config_key": "candidate_branch",
                "pattern": "candidate/dev",
            },
            {
                "role": "work_lane",
                "kind": "branch_prefix",
                "config_key": "work_branch_prefix",
                "pattern": "work/*",
            },
            {
                "role": "submit_lane",
                "kind": "branch_prefix",
                "config_key": "submit_branch_prefix",
                "pattern": "submit/*",
            },
        ],
    }
    assert status["candidate"]["worktree_binding"] == "linked"
    assert status["candidate"]["worktree_path"] == candidate.as_posix()
    assert [binding["branch"] for binding in status["branch_bindings"]] == [
        "main",
        "dev",
        "candidate/dev",
        "work/feature",
        "submit/feature",
    ]
    bindings = {
        binding["branch"]: binding
        for binding in status["branch_bindings"]
    }
    assert bindings["main"]["role"] == "release_root"
    assert bindings["main"]["worktree_binding"] == "unbound"
    assert bindings["dev"]["worktree_binding"] == "current"
    assert bindings["dev"]["worktree_path"] == repo.as_posix()
    assert bindings["candidate/dev"]["worktree_binding"] == "linked"
    assert bindings["candidate/dev"]["worktree_path"] == candidate.as_posix()
    assert bindings["work/feature"]["worktree_binding"] == "linked"
    assert bindings["work/feature"]["worktree_path"] == worktree.as_posix()
    assert bindings["submit/feature"]["role"] == "submit_lane"
    assert bindings["submit/feature"]["worktree_binding"] == "linked"
    assert bindings["submit/feature"]["worktree_path"] == submit.as_posix()
    assert_no_ui_projection(status)


def test_workspace_status_uses_configured_branch_role_policy(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "branch", "stage/dev", "dev")

    git(repo, "checkout", "-b", "review/ready")
    assert workspace_status(repo)["role"] == "submit_lane"

    git(repo, "checkout", "dev")
    git(repo, "checkout", "-b", "lane/feature")
    assert workspace_status(repo)["role"] == "work_lane"

    git(repo, "checkout", "dev")
    status = workspace_status(repo)
    assert status["role"] == "accepted_root"
    assert status["candidate"]["branch"] == "stage/dev"
    assert status["candidate"]["exists"] is True

    git(repo, "branch", "main", "dev")
    git(repo, "checkout", "main")
    assert workspace_status(repo)["role"] == "release_root"


def test_start_work_lane_uses_configured_candidate_and_work_role_policy(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "stage/dev",
        (tmp_path / "repo-stage-dev").as_posix(),
        "dev",
    )
    worktree = tmp_path / "repo-lane-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "lane/feature"
    assert report["base"] == "stage/dev"
    assert git(worktree, "branch", "--show-current") == "lane/feature"


def test_workspace_status_reports_current_work_lane_closeout_support(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "agent:test",
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": [],
    }


def test_workspace_status_projects_work_lane_claim_binding(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        claim_id="sample-trust",
        apply=True,
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "agent:test",
        "claim_id": "sample-trust",
        "claim_binding": "bound",
        "required_gaps": [],
    }


def test_existing_work_lane_claim_binding_can_be_applied_without_restarting_lane(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    report = bind_work_lane_claim(
        root=worktree,
        claim_id="sample-trust",
        apply=True,
    )
    status = workspace_status(worktree)

    assert report["ok"] is True
    assert report["state"] == "bound"
    assert report["branch"] == "work/feature"
    assert report["owner"] == "agent:test"
    assert report["claim_id"] == "sample-trust"
    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "agent:test",
        "claim_id": "sample-trust",
        "claim_binding": "bound",
        "required_gaps": [],
    }


def test_workspace_status_blocks_raw_work_lane_without_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-raw"
    git(repo, "worktree", "add", "-b", "work/raw", worktree.as_posix(), "dev")

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/raw",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "owner": "",
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/raw"],
    }
    assert status["required_gaps"] == ["work_lane_missing_lease:work/raw"]


def test_workspace_status_reports_current_work_lane_closeout_gaps(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")

    status = workspace_status(worktree)

    assert status["closeout_support"]["supported"] is False
    assert status["closeout_support"]["operation"] == "land_to_candidate"
    assert status["closeout_support"]["required_gaps"] == ["work_lane_dirty"]


def test_workspace_status_reports_closeout_owner_from_lane_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )
    status = workspace_status(worktree)

    assert report["ok"] is True
    assert status["closeout_support"]["owner"] == "agent:test"


def test_workspace_status_tolerates_legacy_state_lease_schema(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    state_db = repo / ".ethos" / "state" / "state.sqlite"
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    with sqlite3.connect(state_db) as connection:
        connection.execute(
            """
            create table leases (
              id text primary key,
              owner text not null default '',
              resource text not null default '',
              expires_at text not null default '',
              created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                "lease:legacy",
                "agent:legacy",
                "work/legacy",
                expires_at.isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )

    status = workspace_status(repo)
    leases = active_leases(state_db)

    assert status["role"] == "accepted_root"
    assert leases == [
        {
            "id": "lease:legacy",
            "subject": "work/legacy",
            "owner": "agent:legacy",
            "expires_at": expires_at.isoformat(),
            "payload": {},
        }
    ]


def test_workspace_status_output_validates_against_workspace_status_schema(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")

    validation = validate_schema_instance("workspace-status.schema.json", workspace_status(repo))

    assert validation["ok"] is True
    assert validation["required_gaps"] == []


def test_workspace_status_schema_rejects_ui_projection_fields(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    payload = workspace_status(repo)
    payload["candidate"]["open_action"] = "open_worktree"
    payload["candidate"]["open_label"] = "host-specific label"

    validation = validate_schema_instance("workspace-status.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_workspace_status_reports_missing_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    status = workspace_status(repo)

    assert status["candidate"] == {
        "branch": "candidate/dev",
        "exists": False,
        "head": "",
        "worktree_exists": False,
        "worktree_path": "",
        "worktree_binding": "absent",
    }
    assert "candidate_branch_missing" in status["required_gaps"]


def test_workspace_status_reports_candidate_branch_without_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")

    status = workspace_status(repo)

    assert status["candidate"]["exists"] is True
    assert status["candidate"]["worktree_exists"] is False
    assert status["candidate"]["worktree_path"] == ""
    assert "candidate_worktree_missing" in status["required_gaps"]


def test_prewrite_rejects_tracked_path_from_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "protected_lane_prewrite_blocked"
    assert report["role"] == "accepted_root"


def test_prewrite_allows_owned_work_lane_with_matching_editor_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is True
    assert report["role"] == "work_lane"
    assert report["error"] == ""


def test_prewrite_rejects_work_lane_without_editor_root_binding(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
    )

    assert report["ok"] is False
    assert report["role"] == "work_lane"
    assert report["error"] == "editor_root_missing"


def test_prewrite_rejects_protected_lane_roles(tmp_path: Path) -> None:
    cases = {
        "release_root": ("main",),
        "candidate": ("candidate/dev",),
        "submit_lane": ("submit/review",),
        "other": ("feature/unknown",),
    }
    for role, checkout_args in cases.items():
        repo = init_repo(tmp_path / f"repo-{role}")
        git(repo, "checkout", "-b", *checkout_args)

        report = prewrite_guard(
            root=repo,
            paths=[repo / "README.md"],
            editor_root=repo,
            require_editor_root=True,
        )

        assert report["ok"] is False
        assert report["role"] == role
        assert report["error"] == "protected_lane_prewrite_blocked"


def test_prewrite_rejects_detached_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo-detached")
    git(repo, "checkout", "--detach", "HEAD")

    report = prewrite_guard(
        root=repo,
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["role"] == "detached"
    assert report["error"] == "protected_lane_prewrite_blocked"


def test_start_work_lane_apply_creates_worktree_and_records_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert report["branch"] == "work/feature"
    assert report["worktree"] == {
        "branch": "work/feature",
        "path": worktree.resolve().as_posix(),
        "head": git(worktree, "rev-parse", "HEAD"),
        "role": "work_lane",
        "worktree_binding": "linked",
    }
    assert worktree.exists()
    assert git(worktree, "branch", "--show-current") == "work/feature"
    leases = active_leases(repo / ".ethos" / "state" / "state.sqlite")
    assert [(lease["subject"], lease["owner"]) for lease in leases] == [
        ("work/feature", "agent:test")
    ]


def test_start_work_lane_apply_requires_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "candidate_branch_missing" in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_requires_candidate_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev", "dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "candidate_worktree_missing" in report["required_gaps"]
    assert not worktree.exists()


def test_start_work_lane_apply_rejects_dirty_candidate_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    (candidate / "README.md").write_text("# dirty candidate\n", encoding="utf-8")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["candidate_worktree_dirty"]
    assert not worktree.exists()


def test_start_work_lane_apply_starts_from_candidate_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    candidate_head = git(repo, "rev-parse", "candidate/dev")
    (repo / "README.md").write_text("# changed on dev\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance dev only",
    )
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is True
    assert git(worktree, "rev-parse", "HEAD") == candidate_head
    assert git(repo, "rev-parse", "dev") != candidate_head


def test_start_work_lane_apply_requires_clean_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    current_worktree = tmp_path / "repo-work-current"
    new_worktree = tmp_path / "repo-work-nested"
    git(repo, "worktree", "add", "-b", "work/current", current_worktree.as_posix(), "dev")

    report = start_work_lane(
        root=current_worktree,
        name="nested",
        path=new_worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not new_worktree.exists()


def test_start_work_lane_apply_rejects_dirty_accepted_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        owner="agent:test",
        apply=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["dirty"] is True
    assert "lane_start_requires_clean_accepted_root" in report["required_gaps"]
    assert not worktree.exists()


def test_retire_landed_work_lane_plans_only_merged_lanes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    active = tmp_path / "repo-work-active"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    git(repo, "worktree", "add", "-b", "work/active", active.as_posix(), "dev")
    (active / "README.md").write_text("# active\n", encoding="utf-8")
    git(active, "add", "README.md")
    git(
        active,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "active work",
    )

    report = retire_landed_work_lanes(root=repo)

    assert report["ok"] is True
    assert report["state"] == "planned"
    assert report["required_gaps"] == []
    lanes = {lane["branch"]: lane for lane in report["lanes"]}
    assert lanes["work/landed"]["retire_ready"] is True
    assert lanes["work/landed"]["required_gaps"] == []
    assert lanes["work/active"]["retire_ready"] is False
    assert lanes["work/active"]["required_gaps"] == ["work_lane_not_merged"]


def test_retire_landed_work_lane_apply_requires_branch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")

    report = retire_landed_work_lanes(root=repo, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["retire_branch_required"]
    assert landed.exists()


def test_retire_landed_work_lane_apply_removes_selected_clean_merged_lane(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")

    report = retire_landed_work_lanes(root=repo, branch="work/landed", apply=True)

    assert report["ok"] is True
    assert report["state"] == "retired"
    assert not landed.exists()
    assert git(repo, "branch", "--list", "work/landed") == ""
