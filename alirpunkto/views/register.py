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
from pyramid.request import Request
from pyramid.httpexceptions import HTTPFound
from ..schemas.register_form import RegisterForm
from ..models.candidature import Candidature, CandidatureStates, Candidatures, CandidatureTypes, VotingChoice
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from pyramid_zodbconn import get_connection
from persistent import Persistent
from pyramid.security import ALL_PERMISSIONS, Allow
from .. import _, MAIL_SENDER, LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD
from ldap3 import Server, Connection, ALL, NTLM
from validate_email import validate_email
from dataclasses import dataclass
from pyramid.renderers import render_to_response
from pyramid.i18n import Translator
import random
import hashlib
from cryptography.fernet import Fernet
from pyramid.path import package_path
from pyramid.path import AssetResolver
from transaction import commit
import logging
log = logging.getLogger("alirpunkto")
from ..models import appmaker
from ..utils import (get_candidatures,
                    decrypt_oid,
                    encrypt_oid,
                    generate_math_challenge,
                    is_valid_email,
                    get_candidature_by_oid)

@view_config(route_name='register', renderer='alirpunkto:templates/register.pt')
def register(request):
    """Register view.
    This view allows a candidate to submit their registration on the site.
    The site checks if the candidate is already registered.
    The site check the email by sending a confirmation email to the candidate
    with a challenge.
    If the candidate is not already registered, the site collects their 
    information and sends them a confirmation email.
    The site then creates a candidature object and randomly selects three
    members from the LDAP directory (if possible, otherwise the administrator)
    as voters. The voters are then invited to vote on the candidature.
 
    """
    translator = request.localizer.translate
    candidature = None
    error = None
    # Check if the candidature is already in the request
    if hasattr(request, 'candidature'):
        candidature = request.candidature
    else:
        # If the candidature is not in the request, try to retrieve it from the URL
        encrypted_oid = request.params.get("oid", None)
        if encrypted_oid:
            decrypted_oid = decrypt_oid(encrypted_oid, request.registry.settings['session.secret'])
            candidature = get_candidature_by_oid(decrypted_oid, request)
        else:
            candidature = Candidature() # Create a new candidature
            request.session['candidature'] = candidature # Store the candidature in the session
    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            candidature = request.session['candidature']
            match candidature.state:
                case CandidatureStates.DRAFT:
                    return handle_draft_state(request, candidature)
                case CandidatureStates.EMAIL_VALIDATION:
                    return handle_email_validation_state(request, candidature)
                case CandidatureStates.CONFIRMED_HUMAN:
                    return handle_confirmed_human_state(request, candidature)
                case CandidatureStates.UNIQUE_DATA:
                    # @TODO Traitez l'étape UNIQUE_DATA ici
                    return handle_unique_data_state(request, candidature)
                case CandidatureStates.PENDING:
                    # @TODO Traitez l'étape PENDING ici
                    return handle_pending_state(request, candidature)
                case _:
                    # @TODO Gestion d'autres états ou d'une erreur éventuelle
                    return handle_default_state(request, candidature)

            #@TODO update
                # Generate math challenge
            
            return HTTPFound(location=request.route_url('success'))
        except ValidationFailure as e:
            return {'form': e.render()}
    else:
        schema = RegisterForm().bind(request=request)
        form = deform.Form(schema, buttons=('submit',), translator=translator)
    return {'form': form.render(), 'candidature': candidature, 'error': error}

def handle_draft_state(request, candidature):
    """Handle the draft state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound: the HTTP found response
    """
    email = request.params['email']
    choice = request.params['choice']
    lang = request.params.get('lang', 'en')

    ar = AssetResolver("alirpunkto")
    resolver = ar.resolve(f'locale/{lang}/LC_MESSAGES/check_email.pt')    

    template_path = resolver.abspath()

    # Check email with LDAP
    err = is_valid_email(email, request)
    candidature.email = email
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if choice not in [x for x in dir(CandidatureTypes) if not x.startswith("_")]:
        return {'form': form.render(), 'candidature': candidature,'error': _('invalid_choice')}
    candidature.type = getattr(CandidatureTypes,choice)
    if err != None:
        return {'form': form.render(), 'candidature': candidature, 'error': err['error']}
    candidature.email = email
    # Create Candidature object
    if choice == CandidatureTypes.ORDINARY.name:
        candidature.type = CandidatureTypes.ORDINARY
    elif choice == CandidatureTypes.COOPERATOR.name:
        candidature.type = CandidatureTypes.COOPERATOR
    else:  
        error = _('invalid_choice')
        return {'form': form.render(), 'candidature': candidature, 'error': error}

    # Generate math challenge for the check email, and memorize it in the candidature
    challenge = generate_math_challenge()
    candidature.challenge = challenge
    # Prepare the email informations
    subject = _('email_validation_subject')
    parametter = encrypt_oid(candidature.oid,
        candidature.seed,
        request.registry.settings['session.secret'])
    url = request.route_url('register', _query={'oid': parametter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    # Fill the email body from the `check_email.pt` page template and the informations above
    body = render_to_response(template_path,
        {'challenge': challenge[0],
        'page_register_whith_oid':url,
        'site_url':site_url,
        'site_name':site_name},
        request=request).text
    # Create the email message
    message = Message(
        subject=subject,
        recipients=email,
        body=body
    )
    # Send the email
    mailer = request.registry['mailer']
    status = mailer.send(message)
    if status == None:
        log.error(f"Error while sending check_email to {email}")
        return {'form': form.render(), 'candidature': candidature, 'error': _('email_not_sent')}
    # Because the email is sent asynchronously, we need to change the state of the candidature before sending the email
    log.info(f"check_email will be sent to {email}, URL {url}, OID {candidature.oid}")
    # Change the state of the candidature
    candidature.state = CandidatureStates.EMAIL_VALIDATION
    #
    candidatures = get_candidatures(request)

    candidatures[candidature.oid] = candidature
    # Add candidature to the list of ongoing candidatures
    candidatures.monitored_candidatures[candidature.oid] = candidature
    # Commit the candidature to the database
    transaction = request.tm
    transaction.commit()
    return {'form': form.render(), 'candidature': candidature}
                
def handle_email_validation_state(request, candidature):
    """Handle the email validation state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound: the HTTP found response
    """
    email = candidature.email
    attended_result = candidature.challenge[1]
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=Translator)

    lang = request.params.get('lang', 'en')
    ar = AssetResolver("alirpunkto")
    resolver = ar.resolve(f'locale/{lang}/LC_MESSAGES/check_email.pt')

    import pdb; pdb.set_trace()
    if request.params['challenge'].strip() != str(attended_result):
        return {'form': form.render(), 'candidature': candidature, 'error': _('invalid_challenge')}
    # The challenge is valid, we can continue
    candidature.state = CandidatureStates.CONFIRMED_HUMAN
    # Prepare the email informations
    subject = _('email_candidature_state_changed')
    parametter = encrypt_oid(candidature.oid,
        candidature.seed,
        request.registry.settings['session.secret'])
    url = request.route_url('register', _query={'oid': parametter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    # Fill the email body from the `check_email.pt` page template and the informations above
    body = render_to_response(template_path,
        {'page_register_whith_oid':url,
        'site_url':site_url,
        'site_name':site_name},
        request=request).text
    # Create the email message
    message = Message(
        subject=subject,
        recipients=email,
        body=body
    )
    # Send the email
    mailer = request.registry['mailer']
    status = mailer.send(message)
    if status == None:
        log.error(f"Error while sending check_email to {email}")
        return {'form': form.render(), 'candidature': candidature, 'error': _('email_not_sent')}
    # Because the email is sent asynchronously, we need to change the state of the candidature before sending the email
    log.info(f"candidature_state_change will be sent to {email}, URL {url}, OID {candidature.oid}")
    # Change the state of the candidature
    candidature.state = CandidatureStates.EMAIL_VALIDATION
    # Commit the change of candidature to the database
    transaction = request.tm
    transaction.commit()
    return {'form': form.render(), 'candidature': candidature}

def handle_confirmed_human_state(request, candidature):
    """Handle the confirmed human state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    #@TODO
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=translator)
    return {'form': form.render()}


def handle_unique_data_state(request, candidature):
    """Handle the unique data state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    #@TODO
    pass

def handle_pending_state(request, candidature):
    """Handle the pending state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    #@TODO
    pass

def handle_default_state(request, candidature):
    """Handle the default state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    pass

