# description: Register view
#   A candidate submits their application through the "register" view on the site.
#   The site verifies that the candidate is not already registered.
#   The site collects their information and sends them an email to confirm their application submission.
#   The site creates an application object and randomly selects 3 members from the LDAP members if possible, otherwise the administrator.
#   The site invites voters to vote for or against the application.
# author: Michaël Launay
# date: 2023-06-15

from dataclasses import dataclass
import datetime
from typing import Dict
import deform
from deform import ValidationFailure
from pyramid.view import view_config
from pyramid.request import Request
from pyramid.httpexceptions import HTTPFound
from ..schemas.register_form import RegisterForm
from ..models.candidature import (
    Candidature, CandidatureStates, 
    CandidatureTypes, SEED_LENGTH,
    CandidatureEmailSendStatus, CandidatureData
)
from .. import _
from pyramid.i18n import Translator, get_localizer
from pyramid.path import AssetResolver
import logging
log = logging.getLogger("alirpunkto")
from ..utils import (
    get_candidatures, decrypt_oid, encrypt_oid,
    generate_math_challenges, is_valid_email, get_candidature_by_oid,
    send_email, register_user_to_ldap, get_preferred_language,
    is_valid_password, is_valid_unique_pseudonym
)

def get_local_template(request, pattern_path):
    """
    Return the local template for the given pattern path according to the user's language preference.

    This function attempts to resolve the template path based on the user's preferred language.
    If the resolution fails, it falls back to the default English language.

    Args:
        request (Request): The request object, used to determine the user's preferred language.
        pattern_path (str): The pattern path for which the local template is requested.

    Returns:
        resolver (object): The resolved pattern handler.

    Raises:
        (No explicit exceptions are raised, but errors are logged)
    """

    lang = get_preferred_language(request)
    ar = AssetResolver("alirpunkto")
    try:
        resolver = ar.resolve(pattern_path.format(lang=lang))
    except:
        log.error(f"Error while resolving locale file for {lang} for {pattern_path}, fallback to en")
        resolver = ar.resolve(pattern_path.format(lang="en"))
    return resolver


@view_config(route_name='register', renderer='alirpunkto:templates/register.pt')
def register(request):
    """Register view.
    This view allows a candidate to submit their registration on the site.
    The site checks if the candidate is already registered.
    The site check the email by sending a confirmation email to the candidate
    with a challenge.
    If the candidate is not already registered, the site collects their 
    information and sends the a confirmation email.
    The site then creates a candidature object and randomly selects three
    members from the LDAP directory (if possible, otherwise the administrator)
    as voters. The voters are then invited to vote on the candidature.
 
    """
    translator = request.localizer.translate
    candidature = None
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=[deform.Button('submit',_('submit'))], translator=translator)
    # Check if the candidature is already in the request
    candidatures = get_candidatures(request)
    if 'candidature_oid' in request.session and request.session['candidature_oid'] in candidatures :
        candidature = candidatures[request.session['candidature_oid']]
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
                return {'form': form.render(), 'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes,
                    'error': error,
                    'url_obsolete': True}
            request.session['candidature_oid'] = candidature.oid
        else:
            candidature = Candidature() # Create a new candidature
            request.session['candidature_oid'] = candidature.oid # Store the candidature oid in the session
    if 'submit' in request.POST:
        controls = request.POST.items()
        try:
            match candidature.state:
                case CandidatureStates.DRAFT:
                    return handle_draft_state(request, candidature)
                case CandidatureStates.EMAIL_VALIDATION:
                    return handle_email_validation_state(request, candidature)
                case CandidatureStates.CONFIRMED_HUMAN:
                    return handle_confirmed_human_state(request, candidature)
                case CandidatureStates.UNIQUE_DATA:
                    return handle_unique_data_state(request, candidature)
                case CandidatureStates.PENDING:
                    return handle_pending_state(request, candidature)
                case _:
                    # @TODO Gestion d'autres états ou d'une erreur éventuelle
                    return handle_default_state(request, candidature)

        except ValidationFailure as e:
            return {'form': e.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
    appstruct = {
        'cooperative_number': candidature.oid,
        'pseudonym': candidature.pseudonym,
        'email': candidature.email,
    }
    return {'form': form.render(appstruct=appstruct, i18n=True), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

def send_validation_email(request: Request, candidature: 'Candidature') -> bool:
    """
    Send the validation email to the candidate.
    
    Args:
        request: The request object.
        candidature: The candidature object.
        
    Returns:
        bool: True if the email is successfully sent, False otherwise.
    """
    template_path = get_local_template(request, 'locale/{lang}/LC_MESSAGES/check_email.pt').abspath()

    email = candidature.email # The email to send to.
    challenge = candidature.challenge # The math challenge for email validation.
    localizer = get_localizer(request)
    subject = localizer.translate(_('email_validation_subject'))
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
        'page_register_with_oid': url,
        'site_url': site_url,
        'site_name': site_name
    }

    # Use the send_email from utils.py
    # Put on the stack the action of sending the email wich is done during the commit
    try:
        success = send_email(request, subject, [email], template_path, template_vars)
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
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
        challenge = generate_math_challenges(request)
        candidature.challenge = challenge

        # Send the validation email
        candidature.add_email_send_status(CandidatureEmailSendStatus.IN_PREPARATION, "send_validation_email")

        if not send_validation_email(request, candidature):
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

def send_confirm_validation_email(request: Request,
    candidature: Candidature) -> Dict:
    """Send the confirmation email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        dict: the result of the email sending
    """
    return send_candidature_state_change_email(request,
        candidature,
        "send_confirm_validation_email")

def send_candidature_state_change_email(request: Request,
    candidature: Candidature,
    sending_function_name,
    template_name = None,
    subject = None) -> Dict:
    """Send the candidature state change email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
        sending_function_name (str): the name of the function that sends the email
        template_name (str): the name of the template to use or None to use the default template
        subject (str): the subject of the email or None to use the default subject
    Returns:
        dict: the result of the email sending
    """
    template_name = template_name if template_name else 'locale/{lang}/LC_MESSAGES/candidature_state_change.pt'
    template_path = get_local_template(request, template_name).abspath()
    localizer = get_localizer(request)
    subject = subject if subject else localizer.translate(_('email_candidature_state_changed'))
    email = candidature.email
    seed = candidature.email_send_status_history[-1].seed

    # Prepare the necessary information for the email
    parametter = encrypt_oid(
        candidature.oid,
        seed,
        request.registry.settings['session.secret']
    ).decode()
  
    url = request.route_url('register', _query={'oid': parametter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    #We don't have user yet so we use the email parts befor the @ or pseudonym if it exists
    user = candidature.pseudonym if hasattr(candidature, "pseudonym") else email.split('@')[0]
    
    template_vars = {
        'page_register_with_oid': url,
        'site_url': site_url,
        'site_name': site_name,
        'candidature': candidature,
        'CandidatureStates': CandidatureStates,
        'user': user
    }
    
    # Use the send_email from utils.py
    try:
        # Stack email sending action to be executed at commit
        success = send_email(request, subject, [email], template_path, template_vars)
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
    
    if success:
        candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, sending_function_name)
        return {'success': True}
    else:
        candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, sending_function_name)
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
        transaction = request.tm
        transaction.commit() # User is a human, we can commit the new candidature state
        
        candidature.add_email_send_status(CandidatureEmailSendStatus.IN_PREPARATION, "send_confirm_validation_email")
        send_result = send_confirm_validation_email(request, candidature)
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
    appstruct = {
        'cooperative_number': candidature.oid,
        'email': candidature.email,
    }
    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if 'submit' in request.POST:
        candidatures = get_candidatures(request)
        password = request.params['password']
        password_confirm = request.params['password_confirm']
        pseudonym = request.params['pseudonym']
        is_valid_password_result = is_valid_password(password)
        if is_valid_password_result:
            is_valid_password_result.update({'form': form.render(appstruct=appstruct, i18n=True), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes})
            return is_valid_password_result
        
        if password != password_confirm:
            return {'form': form.render(appstruct=appstruct, i18n=True), 'error': _('passwords_dont_match'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

        is_valid_pseudo_result = is_valid_unique_pseudonym(pseudonym)
        if is_valid_pseudo_result:
            is_valid_pseudo_result.update({'form': form.render(appstruct=appstruct, i18n=True), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes})
            return is_valid_pseudo_result
        
        candidature.pseudonym = pseudonym

        if candidature.type == CandidatureTypes.ORDINARY:
            result = register_user_to_ldap(request, candidature, password)
            if result['status'] == 'error':
                return {'form': form.render(appstruct=appstruct, i18n=True), 'error': result['message'], 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            candidatures.monitored_candidatures.pop(candidature.oid, None)
            candidature.state = CandidatureStates.APPROVED
            email_template = "send_candidature_approuved_email"

        elif candidature.type == CandidatureTypes.COOPERATOR:
            try:
                parameters = {k: request.params[k] for k in CandidatureData.__dataclass_fields__.keys() if k in request.params}
                parameters['birthdate'] = datetime.datetime.strptime(request.params['date'], '%Y-%m-%d').date()
                data = CandidatureData(**parameters)
                candidature.data = data
            except ValidationFailure as e:
                return {'form': form.render(appstruct=appstruct, i18n=True), 'form': e.render(), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            candidature.pseudonym = request.params['pseudonym']
            candidature.state = CandidatureStates.UNIQUE_DATA
            email_template = "send_candidature_pending_email"

        else:
            return {'form': form.render(appstruct=appstruct, i18n=True), 'error': _('invalid_choice'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, email_template)
        except Exception as e:
            log.error(f"Error while commiting candidature {candidature.oid} : {e}")
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, email_template)
    return {'form': form.render(appstruct=appstruct, i18n=True), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

def handle_unique_data_state(request, candidature):
    """Handle the unique data state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    schema = RegisterForm().bind(request=request)
    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if 'submit' in request.POST:
        #Get identity Verification method

        candidatures = get_candidatures(request)
        candidature.state = CandidatureStates.PENDING
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, "send_candidature_pending_email")
        except Exception as e:
            log.error(f"Error while commiting candidature {candidature.oid} : {e}")
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_candidature_pending_email")

    return {'form': form.render(appstruct=appstruct, i18n=True), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}



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

