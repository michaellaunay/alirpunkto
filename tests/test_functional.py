from __future__ import annotations

import pytest

pytestmark = pytest.mark.functional


def test_root_page_renders(testapp):
    response = testapp.get("/", status=200)
    assert "alirpunkto" in response.text.lower()


def test_notfound_page_returns_404(testapp):
    response = testapp.get("/badurl", status=404)
    assert response.status_code == 404


def test_login_page_renders(testapp):
    response = testapp.get("/login", status=200)
    assert "login" in response.text.lower()


def test_register_page_renders(testapp):
    response = testapp.get("/register", status=200, headers={"Accept-Language": "en"})
    assert response.status_code == 200
    assert "form" in response.text.lower()
