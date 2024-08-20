#TODO: Mock ldap



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


def test_register(testapp):
    res = testapp.get('/register', status=200)
    # check the email send form
    assert b'<form method="POST"' in res.body
    assert b'<input class="email-input" type="email" name="email"' in res.body
    assert b'<input type="submit" value="Submit" name="submit"' in res.body

def test_forgot_password(testapp):
    res = testapp.get('/forgot_password', status=200)
    assert b'Forgot your password ?' in res.body
    assert b'<form method="POST">' in res.body
    assert b'<input type="email" id="email" name="email" required>' in res.body
    assert b'<input type="submit" name="submit" value="Submit">' in res.body
