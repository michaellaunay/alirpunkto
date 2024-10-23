#TODO: Mock ldap
from pyramid.i18n import get_localizer, TranslationStringFactory
from bs4 import BeautifulSoup

_ = TranslationStringFactory('alirpunkto')


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
    from alirpunkto.constants_and_globals import LDAP_LOGIN, LDAP_PASSWORD
    from alirpunkto.secret_manager import get_secret
    post = {'username': LDAP_LOGIN, 'password': get_secret(LDAP_PASSWORD), 'form.submitted': 'True'}
    res = testapp.post('/login', post, status=200)
    assert res.status_code == 200
    assert b'Invalid username or password. Please try again' in res.body


def test_register(testapp, mock_generate_math_challenges, dummy_config, dummy_request, mailer_setup):
    """Test the registration page"""
    # Access the registration page
    headers = {'Accept-Language': 'en'}  # Ensure the test runs with the English locale
    res = testapp.get('/register', status=200, headers=headers)
    assert res.status_code == 200
    assert b'<form method="POST"' in res.body

    email = 'nobody@gmail.com'
    # Submit the registration form
    form = {
        'email': email,  # The email must be an active domain because of domain validation
        'choice': 'ORDINARY',
        'submit': 'Submit'
    }

    # mook generate_math_challenges
    res = testapp.post('/register', form, status=200, headers=headers)
    assert res.status_code == 200
    assert "error" not in str(res.html)
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

    import re
    pattern = r"http://.*/register\?oid=([a-zA-Z0-9%]+)"
    match = re.search(pattern, message.body)
    assert match is not None
    oid = match.group(1)

    res = testapp.get(f'/register?oid={oid}', status=200, headers=headers)
    assert res.status_code == 200

    # Post the challenge result to validate the email
    from tests.conftest import mocked_challenges
    form = {
        'result_A': mocked_challenges['A'][1],  # 14
        'result_B': mocked_challenges['B'][1],  # 41
        'result_C': mocked_challenges['C'][1],  # 17
        'result_D': mocked_challenges['D'][1],  # 13
        'submit': 'Submit'
    }
    res = testapp.post(f'/register', form, status=200, headers=headers)
    assert res.status_code == 200

    # Parse the HTML
    soup = res.html

    # Check for input elements
    inputs = soup.find_all('input')

    # Verify the presence of "password" and "email" input fields
    assert any(input_tag.get('type') == 'password' for input_tag in inputs), "Password input not found."
    assert any(input_tag.get('name') == 'fullname' for input_tag in inputs), "Fullname input not found."
    assert any(input_tag.get('name') == 'fullsurname' for input_tag in inputs), "Fullsurname input not found."
    assert any(input_tag.get('name') == 'description' for input_tag in inputs), "Description input not found."
    assert any(input_tag.get('name') == 'date' for input_tag in inputs), "Date input not found."
    assert any(input_tag.get('name') == 'pseudonym' for input_tag in inputs), "Pseudonym input not found."

    selects = soup.find_all('select')
    assert any(choice.get('name') == 'nationality' for choice in selects), "Nationality input not found."
    assert any(choice.get('name') == 'lang1' for choice in selects), "Lang1 input not found."
    assert any(choice.get('name') == 'lang2' for choice in selects), "Lang2 input not found."
    assert any(choice.get('name') == 'lang3' for choice in selects), "Lang3 input not found."

    assert len(mailer.outbox) == 2
    message = mailer.outbox[1]
    expected_subject = localizer.translate(_("email_candidature_state_changed"))
    assert message.recipients == [email]
    assert message.subject == expected_subject
    assert "New Status: CandidatureStates.CONFIRMED_HUMAN" in message.body
    assert "http://example.com/register?oid=" in message.body

    # Prepare the form dictionary to submit the filled-out form
    form = {
        'fullname': 'John Doe',          # Example full name
        'fullsurname': 'Doe',            # Example surname
        'description': 'A brief description about myself.',
        'date': '01/01/1990',            # Example birthdate
        'nationality': 'FR',             # Example nationality (France)
        'pseudonym': 'johndoe123',       # Example pseudonym
        'password': 'Password123#@',      # Example password
        'password_confirm': 'Password123#@',  # Password confirmation
        'lang1': 'en',                   # Preferred language
        'lang2': 'fr',                   # Secondary language
        'lang3': 'es',                   # Tertiary language
        'submit': 'Submit'
    }

    # Submit the filled form
    res = testapp.post(f'/register', form, status=200, headers=headers)
    assert res.status_code == 200
    assert "Your application has been approved." in str(res.html)

def test_forgot_password(testapp):
    res = testapp.get('/forgot_password', status=200)
    assert b'Forgot your password ?' in res.body
    assert b'<form method="POST">' in res.body
    assert b'<input type="email" id="email" name="email" required>' in res.body
    assert b'<input type="submit" name="submit" value="Submit">' in res.body
