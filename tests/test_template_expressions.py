"""Structural lock on template expression syntax.

The template engine here is Chameleon through pyramid_chameleon: TAL
expressions are PYTHON, not Zope path expressions. ``a/b`` therefore
compiles as a division — Python evaluates the right operand first and
dies with ``NameError: b`` before any traversal happens, whether the
key exists or not. That is exactly how the issue-#55/#149 panels of
/modify_member shipped broken (first real-browser deployment, first
crash: the client found it while checking closed tickets). Subscript
the dict (``python: view['key']``) or use attribute access
(``python: obj.attr``); ``default`` and ``nothing`` alternatives on
bare names stay fine.
"""

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A tal attribute whose expression is not explicitly python: and
# contains ident/ident — the Zope-path habit this engine cannot run.
PATH_STYLE = re.compile(
    r'tal:(?:condition|content|repeat|replace|define|attributes)'
    r'\s*=\s*"(?![^"]*python:)[^"]*'
    r'\b[a-zA-Z_][a-zA-Z0-9_]*/[a-zA-Z_]'
)


def test_no_zope_path_expressions_in_the_templates():
    offenders = []
    for path in sorted(glob.glob(os.path.join(
            ROOT, "alirpunkto", "templates", "**", "*.pt"), recursive=True)):
        text = open(path, encoding="utf-8").read()
        for lineno, line in enumerate(text.splitlines(), 1):
            if PATH_STYLE.search(line):
                offenders.append(f"{os.path.relpath(path, ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Zope-path style expressions found — this engine evaluates "
        "python, a/b is a division that dies with NameError:\n"
        + "\n".join(offenders)
    )
