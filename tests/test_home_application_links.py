"""Regression test for opening application links in a new tab (issue #147).

The application links opened in the same tab, so the applications list was lost.
They must open in a new tab, with rel="noopener noreferrer" for safety. Internal
navigation links (login, register, logout, ...) must keep opening in place.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME_PT = os.path.join(ROOT, "alirpunkto", "templates", "home.pt")


def _home():
    with open(HOME_PT, encoding="utf-8") as fh:
        return fh.read()


def test_application_link_opens_in_a_new_tab():
    home = _home()
    # The <a> whose href is the application url must carry target="_blank".
    m = re.search(r"<a\b[^>]*applications\[app_id\]\['url'\][^>]*>", home)
    assert m, "application link anchor not found"
    anchor = m.group(0)
    assert 'target="_blank"' in anchor
    # Security: a _blank link to an external site must not leak window.opener.
    assert "noopener" in anchor
    assert "noreferrer" in anchor


def test_internal_links_stay_in_the_same_tab():
    home = _home()
    # Only the application link should open a new tab.
    assert home.count('target="_blank"') == 1
