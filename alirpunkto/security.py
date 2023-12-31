"""
_summary_ = "Security settings for the application"
see = "https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html"
https://docs.pylonsproject.org/projects/pyramid/en/latest/tutorials/wiki2/authentication.html
# description: Security settings for the application

"""
# description: Login view
# author: Michaël Launay
# date: 2023-07-28

from pyramid.authentication import AuthTktCookieHelper
from pyramid.csrf import CookieCSRFStoragePolicy
from pyramid.request import RequestLocalCache

from .models import users

class AlirPunktoSecurityPolicy:

    def __init__(self, secret):
        self.authtkt = AuthTktCookieHelper(secret)
        self.identity_cache = RequestLocalCache(self.load_identity)


    def load_identity(self, request):
        identity = self.authtkt.identify(request)
        if identity is None:
            return None
        userid = identity['userid']
        user = request.dbsession.query(models.User).get(userid)
        return user


    def identity(self, request):
        return self.identity_cache.get_or_create(request)

    def authenticated_userid(self, request):
        user = self.identity(request)
        if user is not None:
            return user.id

    def remember(self, request, userid, **kw):
        return self.authtkt.remember(request, userid, **kw)

    def forget(self, request, **kw):
        return self.authtkt.forget(request, **kw)


def includeme(config):
    settings = config.get_settings()

    config.set_csrf_storage_policy(CookieCSRFStoragePolicy())
    config.set_default_csrf_options(require_csrf=True)

    config.set_security_policy(AlirPunktoSecurityPolicy(settings['auth.secret']))


