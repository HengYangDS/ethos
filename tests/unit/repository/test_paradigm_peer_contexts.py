"""Closed contexts carry stable names, and each matches what it matched before it was named."""

from __future__ import annotations

import pytest

from ethos.repository.paradigm.peer_identity import CONTEXTS
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import alignment
from ethos.repository.paradigm.peer_identity import numbering
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import redact_text
from ethos.repository.paradigm.peer_identity import replacement_spans

KEY = read_key("ab" * 32)
H1 = "forge.example.invalid"
FEED = Feed.of(hosts=[H1], ports=[8443], ids=[123456789])
# Each named pattern with its source before it was named and a line that it frames.
NAMED = {
    "id.api-projects": (r"projects/(\d+)", "api/v4/projects/123456789/releases"),
    "id.api-projects-encoded": (r"projects%2F(\d+)", "api/v4/projects%2F123456789"),
    "id.ci-project-id": (r"CI_PROJECT_ID[=:] ?(\d+)", "CI_PROJECT_ID: 123456789"),
    "id.project-word": (r"\bproject (\d+)", "the project 123456789 here"),
    "id.id-word": (r"\bID (\d+)", "its ID 123456789 here"),
    "id.project-id-option": (r"--project-id[= \n]+(\d+)", "glab --project-id 123456789"),
    "id.ids-pair": (r"\bIDs \d+ and (\d+)", "IDs 100000001 and 123456789"),
    "id.project-dash": (r"project-(\d+)", "image project-123456789"),
    "id.mise-mirror": (r"-mise-mirror-(\d+)", "in .cache-mise-mirror-123456789/"),
    "id.go-project-id": (r'projectID = "(\d+)"', 'projectID = "123456789"'),
    "id.project-id-key": (r"project_id\"?[=:] ?(\d+)", '{"project_id": 123456789}'),
    "port.word": (r"\bport (\d+)", "listen on port 8443"),
    "port.equals": (r"\bport=(\d+)", "with port=8443"),
    "port.colon": (r"\bport: (\d+)", "port: 8443"),
    "port.json": (r'"port": (\d+)', '{"port": 8443}'),
    "port.key": (r"\w_port[=:] ?(\d+)", "ssh_port=8443"),
    "port.option": (r"--port[= ](\d+)", "serve --port 8443"),
    "port.short-option": (r"(?<![\w-])-p (\d+)", "ssh -p 8443 host"),
}
CACHE = r"\.aigw-ci-cache/(\d+)"


def test_the_named_set_is_stable_and_closed() -> None:
    """Names keep their order, and a record names its ID contexts from this set alone."""
    assert list(CONTEXTS) == [*list(NAMED)[:11], "id.aigw-ci-cache", *list(NAMED)[11:]]


@pytest.mark.parametrize(("name", "case"), list(NAMED.items()))
def test_each_named_context_matches_as_before(name: str, case: tuple[str, str]) -> None:
    """Naming changes no pattern, and the scan gives one result over the digits it frames."""
    source, line = case
    match = CONTEXTS[name].search(line)
    assert CONTEXTS[name].pattern == source
    assert match is not None
    role = name.partition(".")[0]
    found = replacement_spans(line, FEED)
    assert [(span.form, line[span.start : span.end]) for span in found] == [(role, match[1])]


def test_the_aigw_cache_path_joins_the_set_for_every_reader() -> None:
    """An ID under `.aigw-ci-cache/` is replaced, and the keyless reader pairs its number."""
    line = f"cache from {H1} in .aigw-ci-cache/123456789/go\n"
    host, number = replacement_spans(line, FEED)
    redacted = redact_text(line, FEED, KEY, numbering(KEY, FEED, line))
    assert CONTEXTS["id.aigw-ci-cache"].pattern == CACHE
    assert (host.form, number.form, number.context) == ("host", "id", "id.aigw-ci-cache")
    assert "123456789" not in redacted
    assert alignment(line.rstrip("\n"), redacted.rstrip("\n")) == (H1,)
