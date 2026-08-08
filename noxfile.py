"""Thin Nox projection of repository-owned quality sessions."""

import nox

from tools.ci import sessions

nox.options.default_venv_backend = "none"
nox.options.error_on_external_run = True
nox.options.sessions = ["lint"]

for _name in sessions.PUBLIC_SESSIONS:
    _implementation = getattr(sessions, _name)
    _implementation.__name__ = _name
    nox.session(python=False, name=_name)(_implementation)
