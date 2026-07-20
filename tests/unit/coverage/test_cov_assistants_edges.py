from pathlib import Path

import ethos.assistants.playbooks as p
import ethos.assistants.skills.portfolio as f
import ethos.surface.cli.assistants as c


def test_playbook_portfolio_and_cli_edges(tmp_path, monkeypatch) -> None:
    skills = tmp_path / ".agents/skills"
    skills.mkdir(parents=True)
    source = Path(".agents/skills/activation.toml").read_text(encoding="utf-8")
    (skills / "activation.toml").write_text(source, encoding="utf-8")
    report = p.playbooks_report(tmp_path)
    assert ".agents/skills/README.md" in report["required_gaps"]
    assert any(gap.startswith("skill_missing_file:") for gap in report["required_gaps"])
    record = report["registry"]["records"][0]
    record.update(lifecycle="", commands=[])
    record["activation"]["path_globs"] = []
    strict = " ".join(p._strict_record_gaps(record))
    assert all(term in strict for term in ("lifecycle", "path_globs", "commands"))
    assert p._root_relative(tmp_path, tmp_path.as_posix()) == ""
    records = [dict(report["records"][0], id=str(index), intent_tokens=["t"]) for index in range(3)]
    gaps = " ".join(f.portfolio_design(records, [{"id": "0", "files": range(7)}])["required_gaps"])
    assert "package_overloaded:0:7" in gaps
    assert "intent_token_overclaimed:t:0,1,2" in gaps
    assert not f.portfolio_coverage({}, [dict(records[0], primary_subject="")])["owners"]
    seen, emitted = [], []
    payload = {"ok": True, "state": "ready", "summary": {}, "required_gaps": [], "data": {}}
    monkeypatch.setattr(c, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(c, "context_retrieval_smoke_queries", lambda: ("q",))
    monkeypatch.setattr(c, "context_eval_report", lambda *_args, **kw: seen.append(kw["fixtures"]) or payload)  # fmt: skip
    monkeypatch.setattr(c, "emit", lambda result, **kw: emitted.append((result, kw)))
    for suite in ("smoke", "full"):
        c.assistants_context_eval(root=None, suite=suite, json_output=True)
    assert seen == [("q",), ()]
    assert [item.command for item, _kw in emitted] == ["assistants context-eval"] * 2
    assert [kw for _item, kw in emitted] == [{"json_output": True, "enforce": False}] * 2
