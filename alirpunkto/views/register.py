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
    CandidatureEmailSendStatus, CandidatureData,
    Voter
)
from .. import _, MAIL_SIGNATURE
from pyramid.i18n import Translator, get_localizer
import logging
log = logging.getLogger("alirpunkto")
from ..utils import (
    get_candidatures, decrypt_oid,
    generate_math_challenges, is_valid_email, get_candidature_by_oid,
    register_user_to_ldap,
    is_valid_password, is_valid_unique_pseudonym, random_voters,
    send_validation_email,
    send_confirm_validation_email,
    send_candidature_state_change_email,
)

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
    candidature = None
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
            if candidature is None:
                error = _('candidature_not_found')
                return {'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes,
                    'error': error}
            if seed != candidature.email_send_status_history[-1].seed:
                error = _('url_is_obsolete')
                return {'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes,
                    'error': error,
                    'url_obsolete': True}
            request.session['candidature_oid'] = candidature.oid
        else:
            candidature = Candidature() # Create a new candidature
            request.session['candidature_oid'] = candidature.oid # Store the candidature oid in the session
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
        case CandidatureStates.APPROVED:
            return handle_pending_state(request, candidature)
        case CandidatureStates.REFUSED:
            return handle_pending_state(request, candidature)
        case _:
            # @TODO Gestion d'autres états ou d'une erreur éventuelle
            return handle_default_state(request, candidature)

def handle_draft_state(request: Request, candidature: Candidature) -> HTTPFound:
    """Handle the draft state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound: the HTTP found response
    """
    if 'submit' in request.POST:
        email = request.params['email']
        choice = request.params['choice']

        err = is_valid_email(email, request)

        if choice not in CandidatureTypes.get_names():
            return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes,'error': _('invalid_choice')}
        candidature.type = getattr(CandidatureTypes, choice)

        if err is not None:
            return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': err['error']}
        
        candidature.email = email

        # update the candidature
        if choice == CandidatureTypes.ORDINARY.name:
            candidature.type = CandidatureTypes.ORDINARY
        elif choice == CandidatureTypes.COOPERATOR.name:
            candidature.type = CandidatureTypes.COOPERATOR
        else:  
            error = _('invalid_choice')
            return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': error}

        # Generate math challenge for the check email, and memorize it in the candidature
        challenge = generate_math_challenges(request)
        candidature.challenge = challenge

        # Send the validation email
        candidature.add_email_send_status(CandidatureEmailSendStatus.IN_PREPARATION, "send_validation_email")

        if not send_validation_email(request, candidature):
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_validation_email")
            return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error': _('email_not_sent')}

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
    return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes}


def handle_email_validation_state(request, candidature):
    """Handle the email validation state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound or other responses based on the logic
    """
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
                schema = RegisterForm().bind(request=request)
                appstruct = {
                    'cooperative_number': candidature.oid,
                    'email': candidature.email,
                }
                if candidature.type == CandidatureTypes.ORDINARY:
                    schema.prepare_for_ordinary()
                form = deform.Form(schema, buttons=('submit',), translator=Translator)
                return {'form': form.render(appstruct=appstruct), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
                
            except Exception as e:
                log.error(f"Error while commiting candidature {candidature.oid} : {e}")
                candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_confirm_validation_email")
    return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

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
    if candidature.type == CandidatureTypes.ORDINARY:
        schema.prepare_for_ordinary()

    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if 'submit' in request.POST:

        try:
            items = request.POST.items()
            appstruct.update(dict(items))
            #form.validate(items) #@TODO resolve the error 
        except ValidationFailure as e:
            return {'form': form.render(appstruct=appstruct), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
        candidatures = get_candidatures(request)
        password = request.params['password']
        password_confirm = request.params['password_confirm']
        pseudonym = request.params['pseudonym']
        appstruct['pseudonym'] = pseudonym
        is_valid_password_result = is_valid_password(password)
        if is_valid_password_result:
            is_valid_password_result.update({'form': form.render(appstruct=appstruct), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes})
            return is_valid_password_result
        
        if password != password_confirm:
            return {'form': form.render(appstruct=appstruct), 'error': _('passwords_dont_match'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

        is_valid_pseudo_result = is_valid_unique_pseudonym(pseudonym)
        if is_valid_pseudo_result:
            is_valid_pseudo_result.update({'form': form.render(appstruct=appstruct), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes})
            return is_valid_pseudo_result
        
        candidature.pseudonym = pseudonym

        if candidature.type == CandidatureTypes.ORDINARY:
            result = register_user_to_ldap(request, candidature, password)
            if result['status'] == 'error':
                return {'form': form.render(appstruct=appstruct), 'error': result['message'], 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            candidatures.monitored_candidatures.pop(candidature.oid, None)
            candidature.state = CandidatureStates.APPROVED
            email_template = "send_candidature_approuved_email"

        elif candidature.type == CandidatureTypes.COOPERATOR:
            appstruct['fullname'] = request.params['fullname']
            appstruct['fullsurname'] = request.params['fullsurname']
            appstruct['nationality'] = request.params['nationality']
            appstruct['lang1'] = request.params['lang1']
            appstruct['lang2'] = request.params['lang2']
            parameters = {k: request.params[k] for k in CandidatureData.__dataclass_fields__.keys() if k in request.params}
            try:
                parameters['birthdate'] = datetime.datetime.strptime(request.params['date'], '%Y-%m-%d').date()
            except ValueError:
                return {'form': form.render(appstruct=appstruct), 'error': _('invalid_date'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
            data = CandidatureData(**parameters)
            candidature.data = data

            candidature.pseudonym = request.params['pseudonym']
            candidature.state = CandidatureStates.UNIQUE_DATA
            email_template = "send_candidature_pending_email"

        else:
            return {'form': form.render(appstruct=appstruct), 'error': _('invalid_choice'), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

        send_candidature_state_change_email(request, candidature, email_template)
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, email_template)
        except Exception as e:
            log.error(f"Error while commiting candidature {candidature.oid} : {e}")
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, email_template)
    
    return {'form': form.render(appstruct=appstruct), 'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

def handle_unique_data_state(request, candidature):
    """Handle the unique data state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    if not candidature.voters:
        transaction = request.tm
        try:
            voters = random_voters(request)
            candidature.voters = [
                Voter(voter["mail"], voter["sn"])
                for voter in voters
            ]
            transaction.commit()
        except Exception as e:
            log.error(f"Error while commiting candidature {candidature.oid} : {e}")
            return {
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
                'error': _('voters_not_selected'),
                'voting_url': request.route_url('vote', _query={'oid': candidature.oid}),
                'signature': MAIL_SIGNATURE.format(
                    site_name=request.registry.settings.get('site_name'),
                    fullname = candidature.data.fullname,
                    fullsurname = candidature.data.fullsurname,
                )
            }

    if 'confirm' in request.POST:
        #Get identity Verification method

        candidatures = get_candidatures(request)
        candidature.state = CandidatureStates.PENDING
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, "send_candidature_pending_email")
            transaction.commit()
            return {
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
            }

        except Exception as e:
            log.error(f"Error while commiting candidature {candidature.oid} : {e}")
            candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_candidature_pending_email")

    return {
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes,
        'voters': candidature.voters,
        'voting_url': request.route_url('vote', _query={'oid': candidature.oid}),
        'signature': MAIL_SIGNATURE.format(
            site_name=request.registry.settings.get('site_name'),
            fullname = candidature.data.fullname,
            fullsurname = candidature.data.fullsurname if getattr(candidature.data, 'fullsurname', "Alirpunkto team") else "",
        )
    }



def handle_pending_state(request, candidature):
    """Handle the pending state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    return {
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes,
    }

def handle_default_state(request, candidature):
    """Handle the default state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes, 'error':"handle_default_state Not yet implemented"}

