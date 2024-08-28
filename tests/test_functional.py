#TODO: Mock ldap
from alirpunkto.utils import logout
import pytest
from pyramid import testing
from pyramid.i18n import get_localizer, TranslationStringFactory
from unittest.mock import patch

_ = TranslationStringFactory('alirpunkto')

@pytest.fixture
def new_session(testapp):
    # Configure une nouvelle session avant chaque test
    session_factory = testapp.app.registry['session_factory']
    session = session_factory()

    # Injecter la nouvelle session dans la requête
    testapp.app.registry['session'] = session
    return session

def test_root(testapp):
    res = testapp.get('/', status=200)
    assert b'alirpunkto' in res.body

def test_notfound(testapp):
    res = testapp.get('/badurl', status=404)
    assert res.status_code == 404

def test_login(testapp):
    res = testapp.get('/login', status=200)
    assert b'Login' in res.body
    # Mock ldap

    post = {'username': 'admin', 'password': 'admin', 'form.submitted': 'True'}
    res = testapp.post('/login', post, status=200)
    assert res.status_code == 200
    assert b'Invalid username or password. Please try again' in res.body


def test_register(testapp, mock_generate_math_challenges, dummy_config, dummy_request, mailer_setup):
    # Access the registration page
    res = testapp.get('/register', status=200)
    assert b'<form method="POST"' in res.body

    # Submit the registration form
    form = {
        'email': 'nobody@gmail.com',  # The email must be an active domain because of domain validation
        'choice': 'ORDINARY',
        'submit': 'Submit'
    }

    headers = {'Accept-Language': 'en'}  # Ensure the test runs with the English locale
    # mook generate_math_challenges
    res = testapp.post('/register', form, status=200, headers=headers)
    assert res.status_code == 200

    # Check the email sent
    mailer = mailer_setup
    assert len(mailer.outbox) == 1
    message = mailer.outbox[0]
    localizer = get_localizer(dummy_request)
    expected_subject = localizer.translate(_("email_validation_subject"))
    
    assert message.recipients == [form['email']]
    assert message.subject == expected_subject

    # Verify the challenges in the email content
    assert "three times four plus two" in message.body
    assert "five times seven plus six" in message.body
    assert "eight times one plus nine" in message.body
    assert "two times three plus seven" in message.body


def test_forgot_password(testapp):
    res = testapp.get('/forgot_password', status=200)
    assert b'Forgot your password ?' in res.body
    assert b'<form method="POST">' in res.body
    assert b'<input type="email" id="email" name="email" required>' in res.body
    assert b'<input type="submit" name="submit" value="Submit">' in res.body
