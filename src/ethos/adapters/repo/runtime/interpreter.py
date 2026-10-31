"""The interpreter flags of every Python process that ETHOS starts.

Each process writes no bytecode (``-B``), is isolated from the environment, the user site and its
working directory (``-I``), and runs in UTF-8 mode (``-X utf8``): its default file, standard-stream
and pipe encoding is UTF-8 whatever the host locale, as Python 3.15 makes the default. ``-I``
ignores ``PYTHONUTF8``, so the mode is a flag.
"""

PYTHON_FLAGS = ("-B", "-I", "-X", "utf8")
