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
    res = conn.search(LDAP_BASE_DN,
        f'(mail={email.strip()})',
        search_scope=SUBTREE,
        attributes=['cn', 'uid', 'secondLanguage'])
    assert conn.entries[-1].secondLanguage.value == form['lang2'] # why mocked ldap does not retrieve this attribute with other ???
    res = conn.search(LDAP_BASE_DN,
        f'(mail={email.strip()})',
        search_scope=SUBTREE,
        attributes=['cn', 'uid', 'thirdLanguage'])    
    assert conn.entries[-1].thirdLanguage.value == form['lang3'] # Mocked ldap does not retrieve this attribute whith other ???

def test_register_cooperator(testapp, mock_generate_math_challenges, dummy_config, dummy_request, mailer_setup):
    """Test the registration page for cooperator"""
    # Access the registration page
    from alirpunkto.constants_and_globals import ADMIN_EMAIL, DOMAIN_NAME, SITE_NAME
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
    register_pattern = r"http://.*/register\?oid=([a-zA-Z0-9%]+)"
    match = re.search(register_pattern, message.body)
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
        'date': '1999-01-01T00:00:00Z',            # Example birthdate
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
    cooperator_form = form.copy() # backup the form for final check

    # Submit the filled form
    res = testapp.post(f'/register', form, status=200, headers=headers)
    assert res.status_code == 200
    assert "Send a copy of your identity documents by email" in str(res.html), "The message to send the identity documents is not displayed."
    assert "Arrange a video conference meeting" in str(res.html), "The message to arrange a video conference meeting is not displayed."
    assert len(mailer.outbox) == 3
    message = mailer.outbox[2]
    assert message.recipients == [email]
    expected_subject = localizer.translate(_("email_candidature_state_changed"))
    assert message.subject == expected_subject   # @TODO Correct form due to error
    url_mail = re.search(r"http://example.com/register\?oid=([a-zA-Z0-9%]+)", message.body)
    assert url_mail is not None
    oid_value = url_mail.group(1)
    res_mail = testapp.get(f'/register?oid={oid_value}', status=200)
    assert res_mail.html == res.html, "The result page is not the same as the one sent by email."
    # @TODO check the javascript is workging with Selenium
    button_send_email = res.html.find("button")
    assert button_send_email is not None
    assert "data-emails" in button_send_email.attrs
    assert button_send_email.attrs["data-emails"] == ADMIN_EMAIL
    assert button_send_email.attrs["data-user-email"] == email
    assert button_send_email.attrs["email_copy_id_verification_body"]
    vote_pattern = r"http://.*/vote\?oid=([a-zA-Z0-9%-]+)"
    match = re.search(vote_pattern, button_send_email.attrs["email_copy_id_verification_body"])
    assert match is not None, "The vote URL is not in the email body."
    url_vote = match.group(0)

    form = {
        "identity_verification": "email", # The user chooses to send the identity documents by email
        "submit_button": "Confirm"
    }
    # @TODO check "video" option
    res = testapp.post(f'/register', form, status=200)
    assert res.status_code == 200
    res = testapp.post(f'/logout', form, status=302)
    assert res.status_code == 302
    # Admin login
    from alirpunkto.constants_and_globals import ADMIN_LOGIN, ADMIN_PASSWORD
    from alirpunkto.secret_manager import get_secret
    post = {'username': ADMIN_LOGIN, 'password': get_secret(ADMIN_PASSWORD), 'form.submitted': 'True'}
    res = testapp.post('/login', post, status=302)
    assert res.status_code == 302
    res = res.follow()
    assert b'Invalid username or password. Please try again' not in res.body
    # Admin vote
    res = testapp.get(url_vote, status=200)
    assert res.status_code == 200
    assert "Vote for the Candidature" in str(res.html)
    form = res.forms[0]
    assert form is not None, "Vote form not found."
    # verify the form has the vote field
    assert 'vote' in form.fields, "Vote field not found in the form."
    # form.fields is an OrderedDict({'vote': [<Radio name="vote" id="vote_YES">], 'submit': [<Submit name="submit">]})
    # filed the response
    form = {
        'vote': 'YES',
        'submit': 'Submit'
    }
    res = testapp.post(url_vote, form, status=200)
    assert res.status_code == 200
    message = mailer.outbox[-1]
    assert "CandidatureStates.APPROVED" in message.body, "The candidature is not approved."
        #verify the user is in the mocked ldap
    from alirpunkto.constants_and_globals import LDAP_USER, LDAP_PASSWORD, LDAP_BASE_DN
    from ldap3 import SUBTREE
    from alirpunkto.ldap_factory import get_ldap_connection
    from alirpunkto.secret_manager import get_secret
    conn = get_ldap_connection(LDAP_USER, get_secret(LDAP_PASSWORD))
    res = conn.search(LDAP_BASE_DN,
        f'(mail={email.strip()})',
        search_scope=SUBTREE,
        attributes=[
        'cn', 'uid', 'isActive', 'employeeType', 'mail',
        'preferredLanguage', 'sn', 'description'])
    # Due to a bug in the LDAP mock, the request below does not return the attributes 
    assert res == True
    # Due to a bug in the LDAP mock, the request below could not return the attributes in one request
    #uid = conn.entries[-1].uid.value
    #res = conn.search(
    #        LDAP_BASE_DN,
    #        f'(uid={uid})',
    #        attributes=[
    #            'cn', 'mail', 'employeeType', 'sn', 'uid', 
    #            'employeeNumber', 'isActive', 'gn', 'nationality',
    #            'birthdate', 'preferredLanguage', 'secondLanguage',
    #            'cooperativeBehaviourMark',
    #            'cooperativeBehaviorMarkUpdate', 'numberSharesOwned',
    #            'dateEndValidityYearlyContribution', 'uniqueMemberOf',
    #            'iban', 'dateErasureAllData'
    #        ]

    assert res == True
    assert conn.entries[-1].mail.value == email
    assert conn.entries[-1].employeeType.value == 'COOPERATOR'
    assert conn.entries[-1].isActive.value == True
    assert conn.entries[-1].cn.value == cooperator_form['pseudonym']
    assert conn.entries[-1].sn.value == cooperator_form['fullsurname']
    assert conn.entries[-1].preferredLanguage.value == cooperator_form['lang1']
    assert conn.entries[-1].description.value == cooperator_form['description']
    # due to a bug in the LDAP mock, the birthdate is not retrieved directly
    res = conn.search(LDAP_BASE_DN, f'(mail={email.strip()})', search_scope=SUBTREE, attributes=['cn', 'uid','birthdate'])
    assert conn.entries[-1].birthdate.value == cooperator_form['date']
    res = conn.search(LDAP_BASE_DN, f'(mail={email.strip()})', search_scope=SUBTREE, attributes=['cn', 'uid','secondLanguage'])
    assert conn.entries[-1].secondLanguage.value == cooperator_form['lang2'] # why mocked ldap does not retrieve this attribute ???
    res = conn.search(LDAP_BASE_DN, f'(mail={email.strip()})', search_scope=SUBTREE, attributes=['cn', 'uid','thirdLanguage'])
    assert conn.entries[-1].thirdLanguage.value == cooperator_form['lang3'] # Mocked ldap does not retrieve this attribute ???
    res = conn.search(LDAP_BASE_DN, f'(mail={email.strip()})', search_scope=SUBTREE, attributes=['cn', 'uid','nationality'])
    assert conn.entries[-1].nationality.value == cooperator_form['nationality'] # Mocked ldap does not retrieve this attribute ???

def test_forgot_password(testapp):
    res = testapp.get('/forgot_password', status=200)
    assert b'Forgot your password ?' in res.body
    assert b'<form method="POST">' in res.body
    assert b'<input type="email" id="email" name="email" required>' in res.body
    assert b'<input type="submit" name="submit" value="Submit">' in res.body
