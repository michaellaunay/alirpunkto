import deform
from deform import schema, ValidationFailure
from pyramid_handlers import action
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('alirpunkto')

import colander
import deform
from deform import schema

@view_config(route_name='forgot_password', renderer='../templates/forgot_password.pt')
def forgot_password(request):
    """Forgot password view.
    Send an email to the user with a link to reset his password
    
    Args:
        request (pyramid.request.Request): the request
    """
    #@TODO: send an email to the user with a link to reset his password


    return {}
