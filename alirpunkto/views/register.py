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
from .. import _
from ..schemas.register_form import RegisterForm
from ..models.candidature import Candidature, CandidatureStates, Candidatures, CandidatureTypes, VoteTypes
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from pyramid_zodbconn import get_connection
from persistent import Persistent
from pyramid.security import ALL_PERMISSIONS, Allow
from .. import MAIL_SENDER
from .. import LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD
from ldap3 import Server, Connection, ALL, NTLM
from validate_email import validate_email
from dataclasses import dataclass
from pyramid.renderers import render_to_response
from pyramid.i18n import Translator

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
            decrypted_oid = decrypt_oid(encrypted_oid)
            candidature = get_candidature_by_oid(decrypted_oid)
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
    template_path = f"templates/{lang}/LC/check_email.pt"

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
    #@TODO retourner l'oid
    # Create Candidature object
    if choice == CandidatureTypes.ORDINARY:
        candidature.type = CandidatureTypes.ORDINARY
    elif choice == CandidatureTypes.COOPERATOR:
        candidature.type = CandidatureTypes.COOPERATOR
    else:  
        error = _('invalid_choice')
        return {'form': form.render(), 'candidature': candidature, 'error': error}
    # Send email
    challenge = generate_math_challenge()
    candidature.state = CandidatureStates.EMAIL_VALIDATION
    subject = _('email_validation_subject')
    # Fill the email body from the page template and the challenge
    parametter = encrypt_oid(candidature.oid, candidature.seed, request.registry.settings['session.secret'])
    url = request.route_url('register', _query={'oid': oid})
    body = render_to_response(template_path, {'challenge': challenge[0], 'url':url}, request=request).text
    # Create the email message
    message = Message(
        subject=subject,
        recipients=email,
        body=body
    )
    # Send the email
    mailer = get_mailer(request)
    status = mailer.send(message)

                
def handle_email_validation_state(request, candidature):
    """Handle the email validation state.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        HTTPFound: the HTTP found response
    """
    challenge = generate_math_challenge()
    candidature = request.session['candidature']
    email = candidature.email

    
    # Send email (pseudo code)
    send_challenge_email(email, challenge)
    
    # Redirect or inform the user
    return HTTPFound(location=request.route_url('email_validation'))

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

def is_valid_email(email, request):
    """Check if the email is valid and not used in LDAP.

    Args:
        email (str): the email to check
        request (pyramid.request.Request): the request

    Returns:
        error: the error if the email is not valid
        None: if the email is valid
    """
    if not validate_email(email, check_mx=True):
        return {'error': _('invalid_email')}
    try:
        server = Server(LDAP_SERVER, get_info=ALL) # define an unsecure LDAP server, requesting info on DSE and schema
        ldap_login=f"uid={LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" # define the user to authenticate
        conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) # define an unsecure LDAP connection, using the credentials above
        # Verify that the email is not already registered
        conn.search(LDAP_BASE_DN, '(uid={})'.format(email), attributes=['cn']) # search for the user in the LDAP directory
        # Verify that the email is not already registered
        if len(conn.entries) == 0:
            # If already registered, display an error message
            return {'error': _('email_allready_exist')}
    # The email is valid and not already used
    except:
        return {'error': _('ldap_error')}
    return None

def is_valid_unique_pseudo(pseudonym, request):
    """Check if pseudonym is valid and is not already used.

    Args:
        pseudonym (str): the pseudonym to check
        request (pyramid.request.Request): the request

    Returns:
        error: the error if the email is not valid or already used
        None: if the email is valid and not already used
    """
    server = Server(LDAP_SERVER, get_info=ALL) # define an unsecure LDAP server, requesting info on DSE and schema
    ldap_login=f"uid={LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" # define the user to authenticate
    conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) # define an unsecure LDAP connection, using the credentials above
    # Verify that the pseudonym is not already registered
    conn.search(LDAP_BASE_DN, '(uid={})'.format(pseudonym, attributes=['cn'])) # search for the user in the LDAP directory
    # Verify that the candidate is not already registered
    if len(conn.entries) == 0:
        # If already registered, display an error message
        return {'error': _('pseudonym_allready_exists')}
    return None

def generate_math_challenge():
    """Generate a math challenge.
    return:
        tuple: a tuple containing the str math challenge and 0 to 9 numvers uses to generate the challenge
    """
    numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    num1 = random.choice(numbers)
    str_num1 = _(num1)
    num2 = random.choice(numbers)
    str_num2 = _(num2)
    num3 = random.choice(numbers)
    str_num3 = _(num3)
    num4 = random.choice(numbers)
    str_num4 = _(num4)
    num5 = random.choice(numbers)
    str_num5 = _(num5)

    return (f"({str_num1} + {str_num2}) * ({str_num3} + {str_num4}) + {str_num5}", num1 + num2 * num3 + num4 + num5)

def get_candidature_from_request(request: Request)->Candidature:
    """Get the candidature from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature
    """
    encrypted_oid = request.params.get("oid")

    decrypted_oid = decrypt_oid(encrypted_oid)
    return get_candidature_by_oid(decrypted_oid)


def decrypt_oid(encrypted_oid: str, seed:str, secret:str)->str:
    """ Function to decrypt the OID using the SECRET and return the decrypted OID
    Args:
        encrypted_oid (str): The encrypted OID
        secret (str): The secret to use to decrypt the OID
    Returns:
        str: The decrypted OID
    """
    m = hashlib.sha256()
    m.update((encrypted_oid + secret).encode())
    return m.hexdigest()


def encrypt_oid(oid, seed, secret) -> tuple[str,str]:
    """ Function to encrypt the OID using the SECRET and return the encrypted OID
    Args:
        oid (str): The OID to encrypt
        seed_size (int): The seed size
        secret (str): The secret to use to encrypt the OID
    Returns:
        str: The encrypted OID
    """
    concatenated_string = oid + seed
    m = hashlib.sha256()
    m.update((concatenated_string + secret).encode())
    # On supprime la graine
    enc = m.hexdigest()
    return enc