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
    res = testapp.post('/login', post, status=302)
    assert res.status_code == 302


def test_register(testapp):
    res = testapp.get('/register', status=200)
    assert b'Register' in res.body

def test_forgot_password(testapp):
    res = testapp.get('/forgot_password', status=200)
    assert b'Forgot password' in res.body
