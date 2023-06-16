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

@view_config(route_name='forgot_password', renderer='templates/forgot_password.pt')
def forgot_password(request):
    # Votre code pour gérer l'oubli du mot de passe va ici
    # Vous pouvez utiliser la fonction send_email pour envoyer un email
    # à l'utilisateur avec un lien pour réinitialiser son mot de passe
    #@TODO: send an email to the user with a link to reset his password

    return {}
