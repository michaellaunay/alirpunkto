# description: Register view
#   A candidate submits their application through the "register" view on the site.
#   The site verifies that the candidate is not already registered.
#   The site collects their information and sends them an email to confirm their application submission.
#   The site creates an application object and randomly selects 3 members from the LDAP members if possible, otherwise the administrator.
#   The site invites voters to vote for or against the application.
# author: Michaël Launay
# date: 2023-06-15

from typing import Dict, Union, Tuple
import deform
from deform import ValidationFailure
from pyramid_handlers import action
from pyramid.view import view_config
from pyramid.request import Request
from pyramid.httpexceptions import HTTPFound
from ..schemas.register_form import RegisterForm
from ..models.candidature import (
    Candidature, CandidatureStates, Candidatures,
    CandidatureTypes, VotingChoice, SEED_LENGTH,
    CandidatureEmailSendStatus
)
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from pyramid_zodbconn import get_connection
from persistent import Persistent
from pyramid.security import ALL_PERMISSIONS, Allow
from .. import (
    _, MAIL_SENDER, LDAP_SERVER, LDAP_OU, LDAP_BASE_DN,
    LDAP_LOGIN, LDAP_PASSWORD
)
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
from ..utils import (
    get_candidatures, decrypt_oid, encrypt_oid,
    generate_math_challenges, is_valid_email, get_candidature_by_oid,
    send_email, register_user_to_ldap
)

MIN_PASSWORD_LENGTH = 12 # Minimum password length
MAX_PASSWORD_LENGTH = 92 # Maximum password length

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
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=translator)
    # Check if the candidature is already in the request
    if 'candidature' in request.session :
        candidature = request.session['candidature']
    else:
        # If the candidature is not in the request, try to retrieve it from the URL
        encrypted_oid = request.params.get("oid", None)
        if encrypted_oid:
            decrypted_oid, seed = decrypt_oid(
                encrypted_oid,
                SEED_LENGTH,
                request.registry.settings['session.secret'])
            candidature = get_candidature_by_oid(decrypted_oid, request)
            schema = RegisterForm().bind(request=request)
            form = deform.Form(schema, buttons=('submit',), translator=translator)
            if seed != candidature.email_send_status_history[-1].seed:
                error = _('url_is_obsolete')
                return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': error, 'url_obsolete': True}
            request.session['candidature'] = candidature
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

        except ValidationFailure as e:
            return {'form': e.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
    return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

def send_validation_email(request: Request, candidature: 'Candidature', email: str, challenge: Dict) -> bool:
    """
    Send the validation email to the candidate.
    
    Args:
        request: The request object.
        candidature: The candidature object.
        email: The email to send to.
        challenge: The math challenge for email validation.
        
    Returns:
        bool: True if the email is successfully sent, False otherwise.
    """
    
    lang = request.params.get('lang', 'en')
    ar = AssetResolver("alirpunkto")
    resolver = ar.resolve(f'locale/{lang}/LC_MESSAGES/check_email.pt')
    template_path = resolver.abspath()

    subject = _('email_validation_subject')
    seed = candidature.email_send_status_history[-1].seed
    parametter = encrypt_oid(candidature.oid, seed, request.registry.settings['session.secret']).decode()
    
    url = request.route_url('register', _query={'oid': parametter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    
    template_vars = {
        'challenge_A': challenge["A"][0],
        'challenge_B': challenge["B"][0],
        'challenge_C': challenge["C"][0],
        'challenge_D': challenge["D"][0],
        'page_register_whith_oid': url,
        'site_url': site_url,
        'site_name': site_name
    }

    # Use the send_email from utils.py
    success = send_email(request, subject, [email], template_path, template_vars)

    return success

def handle_draft_state(request: Request, candidature: Candidature) -> HTTPFound:
    """Handle the draft state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound: the HTTP found response
    """
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=Translator)

    if 'submit' in request.POST:
        email = request.params['email']
        choice = request.params['choice']
        lang = request.params.get('lang', 'en')

        err = is_valid_email(email, request)

        if choice not in CandidatureTypes.get_names():
            return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes,'error': _('invalid_choice')}
        candidature.type = getattr(CandidatureTypes, choice)

        if err is not None:
            return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': err['error']}
        
        candidature.email = email

        # update the candidature
        if choice == CandidatureTypes.ORDINARY.name:
            candidature.type = CandidatureTypes.ORDINARY
        elif choice == CandidatureTypes.COOPERATOR.name:
            candidature.type = CandidatureTypes.COOPERATOR
        else:  
            error = _('invalid_choice')
            return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': error}

        # Generate math challenge for the check email, and memorize it in the candidature
        challenge = generate_math_challenges()
        candidature.challenge = challenge

        # Send the validation email
        candidature.add_email_send_status(CandidatureEmailSendStatus.IN_PREPARATION, "send_validation_email")

        if not send_validation_email(request, candidature, email, challenge=challenge):
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_validation_email")
            return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': _('email_not_sent')}

        # Change the state of the candidature
        candidature.state = CandidatureStates.EMAIL_VALIDATION

        candidatures = get_candidatures(request)
        candidatures[candidature.oid] = candidature
        candidatures.monitored_candidatures[candidature.oid] = candidature

        # Commit the candidature to the database
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, "send_validation_email")
        except Exception as e:
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_validation_email")
            log.error(f"Error while commiting candidature {candidature.oid} : {e}")
    return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

def send_confirm_validation_email(request: Request, candidature: Candidature, email_content: Dict) -> Dict:
    """Send the confirmation email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
        email_content (dict): the content of the email
    Returns:
        dict: the result of the email sending
    """
    lang = request.params.get('lang', 'en')
    ar = AssetResolver("alirpunkto")
    resolver = ar.resolve(f'locale/{lang}/LC_MESSAGES/candidature_state_change.pt')    
    template_path = resolver.abspath()
    
    subject = _('email_candidature_state_changed')
    email = candidature.email
    seed = candidature.email_send_status_history[-1].seed
    parametter = encrypt_oid(candidature.oid, seed, request.registry.settings['session.secret']).decode()
    
    url = request.route_url('register', _query={'oid': parametter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    
    template_vars = {
        'page_register_with_oid': url,
        'challenge_A': candidature.challenge["A"][0],
        'challenge_B': candidature.challenge["B"][0],
        'challenge_C': candidature.challenge["C"][0],
        'challenge_D': candidature.challenge["D"][0],
        'site_url': site_url,
        'site_name': site_name,
        'candidature': candidature,
        'CandidatureStates': CandidatureStates,
        site_name: site_name
    }
    
    # Use the send_email from utils.py
    success = send_email(request, subject, [email], template_path, template_vars)
    
    if success:
        candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, "send_confirm_validation_email")
        return {'success': True}
    else:
        candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_confirm_validation_email")
        return {'error': _('email_not_sent')}

def handle_email_validation_state(request, candidature):
    """Handle the email validation state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound or other responses based on the logic
    """
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if 'submit' in request.POST:
        # Extract the expected result of the challenge from the candidature
        attended_results = candidature.challenge
        for key, attended_result in attended_results.items():
            attended_result = str(attended_result[1])
            label = f"result_{key}"
            if request.params[label].strip() != attended_result:
                return {'error': _('invalid_challenge'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            
        # Correct, we can continue and change the state of the candidature
        candidature.state = CandidatureStates.CONFIRMED_HUMAN
        
        # Préparer les informations nécessaires pour l'email
        subject = 'email_candidature_state_changed'
        parametter = encrypt_oid(
            candidature.oid,
            candidature.seed,
            request.registry.settings['session.secret']
        )
        url = request.route_url('register', _query={'oid': parametter})
        site_url = request.route_url('home')
        site_name = request.registry.settings.get('site_name')
        
        # Créer le contenu de l'email à partir des informations ci-dessus
        email_content = {
            'subject': subject,
            'page_register_with_oid': url,
            'site_url': site_url,
            'site_name': site_name
        }
        candidature.add_email_send_status(CandidatureEmailSendStatus.IN_PREPARATION, "send_confirm_validation_email")
        send_result = send_confirm_validation_email(request, candidature, email_content)
        if 'error' in send_result:
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_confirm_validation_email")
        else:
            candidatures = get_candidatures(request)
            candidatures.monitored_candidatures[candidature.oid] = candidature
            transaction = request.tm
            try:
                transaction.commit()
                candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, "send_confirm_validation_email")
            except Exception as e:
                log.error(f"Error while commiting candidature {candidature.oid} : {e}")
                candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_confirm_validation_email")
    return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

def handle_confirmed_human_state(request, candidature):
    """Handle the confirmed human state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if 'submit' in request.POST:
        min_length = MIN_PASSWORD_LENGTH
        max_length = MAX_PASSWORD_LENGTH
        candidatures = get_candidatures(request)
        if candidature.type == CandidatureTypes.ORDINARY:
            password = request.params['password']
            password_confirm = request.params['password_confirm']
            pseudonym = request.params['pseudonym']
            #!!!!! TODO éviter injection dans LDAP !!!!!
            if password != password_confirm:
                return {'error': _('passwords_dont_match'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if len(password) < min_length:
                return {'error': _('password_too_short')+_("password_minimum_length").format(min_length), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if len(password) > max_length:
                return {'error': _('password_too_long')+_("password_maximum_length").format(max_length), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if not any(char.isdigit() for char in password):
                return {'error': _('password_must_contain_digit'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if not any(char.isupper() for char in password):
                return {'error': _('password_must_contain_uppercase'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if not any(char.islower() for char in password):
                return {'error': _('password_must_contain_lowercase'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if not any(char in ['$', '@', '#', '%', '&', '*', '(', ')', '-', '_', '+', '='] for char in password):
                return {'error': _('password_must_contain_special_char'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if len(pseudonym) < min_length:
                return {'error': _('pseudonym_too_short')+_("pseudonym_minimum_length").format(min_length), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            if len(pseudonym) > max_length:
                return {'error': _('pseudonym_too_long')+_("pseudonym_maximum_length").format(max_length), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            #!! Vérifier l'unicité du pseudonyme dans LDAP !!
            candidature.password = password
            candidature.pseudonym = pseudonyme

            register_user_to_ldap(request, candidature, password)
            candidatures.monitored_candidatures.pop(candidature.oid, None)
            candidature.state = CandidatureStates.APPROVED
            transaction = request.tm
            try:
                transaction.commit()
                candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, "send_candidature_approuved_email")
            except Exception as e:
                log.error(f"Error while commiting candidature {candidature.oid} : {e}")
                candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_candidature_approuved_email")
    return {'form': form.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

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

