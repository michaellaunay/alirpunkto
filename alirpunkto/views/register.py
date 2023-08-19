# description: Register view
#   A candidate submits their application through the "register" view on the site.
#   The site verifies that the candidate is not already registered.
#   The site collects their information and sends them an email to confirm their application submission.
#   The site creates an application object and randomly selects 3 members from the LDAP members if possible, otherwise the administrator.
#   The site invites voters to vote for or against the application.
# author: Michaël Launay
# date: 2023-06-15

import deform
from deform import schema, ValidationFailure
import colander
from pyramid_handlers import action
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from ldap3 import Server, Connection, ALL, NTLM
from .. import _
from .. import LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD
from ..schemas.register_form import RegisterForm
from ..models.candidature import Candidature
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from pyramid_zodbconn import get_connection
from persistent import Persistent
from pyramid.security import ALL_PERMISSIONS, Allow
from .. import MAIL_SENDER


# _ is used to translate strings
from .. import _

@view_config(route_name='register', renderer='alirpunkto:templates/register.pt')
def register(request):
    """Register view.
    This view allows a candidate to submit their registration on the site.
    The site checks if the candidate is already registered.
    If the candidate is not already registered, the site collects their 
    information and sends them a confirmation email.
    The site then creates a candidature object and randomly selects three
    members from the LDAP directory (if possible, otherwise the administrator)
    as voters. The voters are then invited to vote on the candidature.    
    """
    schema = RegisterForm().bind(request=request)
    translator = request.localizer.translate
    form = deform.Form(schema, buttons=('submit',), translator=translator)

    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            appstruct = form.validate(controls)
            server = Server(LDAP_SERVER, get_info=ALL) # define an unsecure LDAP server, requesting info on DSE and schema
            ldap_login=f"uid={LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" # define the user to authenticate
            conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) # define an unsecure LDAP connection, using the credentials above
            # Verify that the pseudonym is not already registered
            conn.search(LDAP_BASE_DN, '(uid={})'.format(appstruct['pseudonym']), attributes=['cn']) # search for the user in the LDAP directory
            # Verify that the candidate is not already registered
            if len(conn.entries) == 0:
                # If already registered, display an error message
                return {'error': request.translate(_('pseudonym_allready_exists'))}
            # Verify that the email is not already registered
            conn.search(LDAP_BASE_DN, '(uid={})'.format(appstruct['email']), attributes=['cn']) # search for the user in the LDAP directory
            # Verify that the email is not already registered
            if len(conn.entries) == 0:
                # If already registered, display an error message
                return {'error': request.translate(_('email_allready_exist'))}
            
            # Not registered
            #     Send an email to confirm the submission of their application to the candidate
            

#     If the sending of the email fails, the site displays an error message
#     Otherwise:
#         Create an application object with a unique OUID that can be passed as a URL parameter
#         Draw 3 members at random among the LDAP members if possible, otherwise the administrator
#         Register the voters in the `voters` dictionary of the application object
#         Record the date of submission of the application
#         Add a "status" attribute which is "pending" by default
#         Add a "votes" attribute which is an empty dictionary
#         Record the application object in the ZODB
#         Send an email requesting a vote (vote.pt template by passing the identifier of the application) to accept or reject the application to the voters
#         If the sending of the email fails, the site displays an error message
#         Otherwise:
#             The site displays a success message and invites the candidate to check their email to find out the result of their application
            return HTTPFound(location=request.route_url('success'))
        except ValidationFailure as e:
            return {'form': e.render()}

    return {'form': form.render()}
