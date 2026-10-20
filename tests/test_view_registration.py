"""Every route serves the view it names (issue #268).

The "Forgot password" link answered "Internal server error - Generated
by waitress": the #248 helper ``_display_in_member_language(request,
member)`` had slid between ``@view_config`` and ``def forgot_password``,
so the route registered the helper. Pyramid called it as a
``(context, request)`` view, it returned None, and the Chameleon renderer
refused the non-dictionary. The unit tests never saw it — they call the
function, not the route. These locks go through the registry and the
real WSGI pipeline, for every view module at once.
"""
from __future__ import annotations

import ast
import os

import pytest

VIEWS_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'alirpunkto', 'views')


def _registered_views(app):
    """(route_name, callable name) of every view the app registered."""
    introspector = app.registry.introspector
    pairs = []
    for intr in introspector.get_category('views') or ():
        view = intr['introspectable']
        route_name = view.get('route_name')
        callable_ = view.get('callable')
        if route_name and callable_ is not None:
            pairs.append((route_name, getattr(callable_, '__name__', '?')))
    return pairs


def test_the_forgot_password_route_serves_the_forgot_password_view(app):
    names = {name for route, name in _registered_views(app)
             if route == 'forgot_password'}
    assert names == {'forgot_password'}


def test_no_route_is_served_by_a_private_helper(app):
    """A ``_``-prefixed function is never a view: a decorator that
    lands on one has slid off its view."""
    leaked = [(route, name) for route, name in _registered_views(app)
              if name.startswith('_')]
    assert leaked == []


@pytest.mark.functional
def test_the_forgot_password_page_renders(testapp):
    response = testapp.get('/forgot_password', status=200)
    assert 'email' in response.text.lower()


def _decorated_functions():
    for filename in sorted(os.listdir(VIEWS_DIR)):
        if not filename.endswith('.py'):
            continue
        with open(os.path.join(VIEWS_DIR, filename), encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(
                    decorator, ast.Call) else decorator
                name = getattr(target, 'attr', getattr(target, 'id', ''))
                if name == 'view_config':
                    yield filename, node.name


def test_view_config_only_decorates_public_functions():
    """Source-level twin of the registry lock, so the failure names the
    file even when the app cannot be built."""
    private = [(f, n) for f, n in _decorated_functions()
               if n.startswith('_')]
    assert private == []
