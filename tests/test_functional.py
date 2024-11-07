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
    # Test the login page
    res = testapp.get('/login', status=200)
    assert b'Login' in res.body
    from alirpunkto.constants_and_globals import ADMIN_LOGIN, ADMIN_PASSWORD
    from alirpunkto.secret_manager import get_secret
    # Test the login with the admin credentials
    post = {'username': ADMIN_LOGIN, 'password': get_secret(ADMIN_PASSWORD), 'form.submitted': 'True'}
    res = testapp.post('/login', post, status=302)
    assert res.status_code == 302
    res = res.follow()
    assert b'Invalid username or password. Please try again' not in res.body
    # Test the logout
    res = testapp.get('/logout', status=302)
    assert res.status_code == 302
    res = res.follow()
    assert b'login' in res.body
    # Test the login with a wrong password

def test_register_ordinary(testapp, mock_generate_math_challenges, dummy_config, dummy_request, mailer_setup):
    """Test the registration page"""
    # Access the registration page for ordinary user
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
    assert not any(input_tag.get('name') == 'fullname' for input_tag in inputs), "Full name must not be asked for ordinary user."
    assert not any(input_tag.get('name') == 'fullsurname' for input_tag in inputs), "Full surname must not be asked for ordinary user."
    assert any(input_tag.get('name') == 'description' for input_tag in inputs), "Description input not found."
    assert not any(input_tag.get('name') == 'birthdate' for input_tag in inputs), "Burth date  must not be asked for ordinary user."
    assert any(input_tag.get('name') == 'pseudonym' for input_tag in inputs), "Pseudonym input not found."

    selects = soup.find_all('select')
    assert not any(choice.get('name') == 'nationality' for choice in selects), "Nationality input must not be asked for ordinary user."
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
        'description': 'A brief description about myself.',
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
    #verify the user is in the mocked ldap
    from alirpunkto.constants_and_globals import LDAP_USER, LDAP_PASSWORD, LDAP_BASE_DN
    from ldap3 import SUBTREE
    from alirpunkto.ldap_factory import get_ldap_connection
    from alirpunkto.secret_manager import get_secret
    conn = get_ldap_connection(LDAP_USER, get_secret(LDAP_PASSWORD))
    res = conn.search(LDAP_BASE_DN,
        f'(mail={email.strip()})',
        search_scope=SUBTREE,
        attributes=['cn', 'uid', 'isActive', 'employeeType', 'mail',
        'preferredLanguage', 'sn', 'description'])
    assert res == True
    assert conn.entries[-1].mail.value == email
    assert conn.entries[-1].employeeType.value == 'ORDINARY'
    assert conn.entries[-1].isActive.value == True
    assert conn.entries[-1].cn.value == form['pseudonym']
    assert conn.entries[-1].sn.value == form['pseudonym'] # For ordinary users, the speudonyme is stored as the sn attribute
    assert conn.entries[-1].preferredLanguage.value == form['lang1']
    #assert conn.entries[-1].secondLanguage.value == form['lang2'] # why mocked ldap does not retrieve this attribute ???
    #assert conn.entries[-1].thirdLanguage.value == form['lang3'] # Mocked ldap does not retrieve this attribute ???

def test_register_cooperator(testapp, mock_generate_math_challenges, dummy_config, dummy_request, mailer_setup):
    """Test the registration page for cooperator"""
    # Access the registration page
    headers = {'Accept-Language': 'en'}  # Ensure the test runs with the English locale
    res = testapp.get('/register', status=200, headers=headers)
    assert res.status_code == 200
    assert b'<form method="POST"' in res.body

    email = 'somebody@gmail.com'
    # Submit the registration form
    form = {
        'email': email,  # The email must be an active domain because of domain validation
        'choice': 'COOPERATOR',
        'submit': 'Submit'
    }

    # mook generate_math_challenges
    res = testapp.post('/register', form, status=200, headers=headers)
    assert res.status_code == 200
    assert "error" not in str(res.html)
    # Check the email sent
    mailer = mailer_setup
    assert len(mailer.outbox) == 1
    message = mailer.outbox[-1]
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

    # birthdate input is a bit obvious
    assert any(input_tag.get('name') == '__start__' and input_tag.get('value') == 'birthdate:mapping' for input_tag in inputs), "Birthdate input not found."
    assert any(input_tag.get('name') == 'date' for input_tag in inputs), "Birthdate input not found."
    assert any(input_tag.get('name') == '__end__' and input_tag.get('value') == 'birthdate:mapping' for input_tag in inputs), "Birthdate input not found."

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
        'fullname': 'Jahn Doe',          # Example full name
        'fullsurname': 'Doe',            # Example surname
        'description': 'A brief description about myself.',
        '__start__': 'birthdate:mapping',
        'date': '1999-01-01',            # Example birthdate
        '__end__': 'birthdate:mapping',
        'nationality': 'FR',             # Example nationality (France)
        'pseudonym': 'jahndoe321',       # Example pseudonym
        'password': 'Password321#@',      # Example password
        'password_confirm': 'Password321#@',  # Password confirmation
        'lang1': 'en',                   # Preferred language
        'lang2': 'fr',                   # Secondary language
        'lang3': 'es',                   # Tertiary language
        'submit': 'Submit'
    }

    # Submit the filled form
    res = testapp.post(f'/register', form, status=200, headers=headers)
    assert res.status_code == 200
    # @TODO Correct form due to error

def test_forgot_password(testapp):
    res = testapp.get('/forgot_password', status=200)
    assert b'Forgot your password ?' in res.body
    assert b'<form method="POST">' in res.body
    assert b'<input type="email" id="email" name="email" required>' in res.body
    assert b'<input type="submit" name="submit" value="Submit">' in res.body
