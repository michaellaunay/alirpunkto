# Definition of the functions used in the project
# author: Michaël Launay
# date: 2023-09-30

from typing import Dict
from pyramid.request import Request
from .models.candidature import Candidature, Candidatures
from pyramid_mailer.message import Message, Attachment
from pyramid_zodbconn import get_connection
from . import _, MAIL_SENDER, LDAP_SERVER, LDAP_OU, LDAP_BASE_DN, LDAP_LOGIN, LDAP_PASSWORD, EUROPEAN_LOCALES
from pyramid.i18n import get_localizer
from ldap3 import Server, Connection, ALL
from validate_email import validate_email
from pyramid.renderers import render_to_response
import random
import hashlib
from cryptography.fernet import Fernet
import logging
log = logging.getLogger("alirpunkto")
import base64
import bcrypt
import re

MIN_PSEUDONYM_LENGTH = 5 # Minimum pseudonym length
MAX_PSEUDONYM_LENGTH = 20 # Maximum pseudonym length

pseudonym_pattern = re.compile(f'^[a-zA-Z0-9_.-]{{{MIN_PSEUDONYM_LENGTH},{MAX_PSEUDONYM_LENGTH}}}$')

MIN_PASSWORD_LENGTH = 12 # Minimum password length
MAX_PASSWORD_LENGTH = 92 # Maximum password length

def get_preferred_language(request: Request)->str:
    """Get the preferred language from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        str: the preferred language
    """
    # Get the preferred language from the request
    preferred_language = request.accept_language.best_match(EUROPEAN_LOCALES)
    if preferred_language is None:
        preferred_language = "en"
    return preferred_language

def get_candidatures(request)->Candidatures:
    """Get the candidatures from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidatures: the candidatures
    """
    conn = get_connection(request)
    return Candidatures.get_instance(connection=conn)

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
        ldap_login=f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"# define the user to authenticate
        conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) # define an unsecure LDAP connection, using the credentials above

        # Verify that the email is not already registered
        conn.search(LDAP_BASE_DN, '(uid={})'.format(email), attributes=['cn']) # search for the user in the LDAP directory
        # Verify that the email is not already registered
        if len(conn.entries) != 0:
            # If already registered, display an error message
            return {'error': _('email_allready_exist')}
    # The email is valid and not already used
    except:
        return {'error': _('ldap_error')}
    return None

def is_valid_unique_pseudonym(pseudonym):
    """Check if pseudonym is valid and is not already used.

    Args:
        pseudonym (str): the pseudonym to check

    Returns:
        error: the error if the email is not valid or already used
        None: if the email is valid and not already used
    """
    if not pseudonym_pattern.match(pseudonym):
        return {'error': _('invalid_pseudonym')}

    if len(pseudonym) < MIN_PSEUDONYM_LENGTH:
        return {'error': _('pseudonym_too_short'), 'error_details':_("pseudonym_minimum_length")}
    if len(pseudonym) > MAX_PSEUDONYM_LENGTH:
        return {'error': _('pseudonym_too_long'), 'error_details':_("pseudonym_maximum_length")}

    server = Server(LDAP_SERVER, get_info=ALL) # define an unsecure LDAP server, requesting info on DSE and schema
    ldap_login=f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}" # define the user to authenticate
    conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) # define an unsecure LDAP connection, using the credentials above
    # Verify that the pseudonym is not already registered
    conn.search(LDAP_BASE_DN, '(uid={})'.format(pseudonym, attributes=['cn'])) # search for the user in the LDAP directory
    # Verify that the candidate is not already registered
    if len(conn.entries) != 0:
        # If already registered, display an error message
        return {'error': _('pseudonym_allready_exists')}
    # The pseudonym is valid and not already used
    return None

def is_valid_password(password):
    """Check if the password is valid.

    Args:
        password (str): the password to check

    Returns:
        error: the error if the password is not valid
        None: if the password is valid
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return {'error': _('password_too_short'), 'error_details':_("password_minimum_length", mapping={'password_minimum_length':MIN_PASSWORD_LENGTH})}
    if len(password) > MAX_PASSWORD_LENGTH:
        return {'error': _('password_too_long'), 'error_details':_("password_maximum_length", mapping={'password_maximum_length':MAX_PASSWORD_LENGTH})}
    if not any(char.isdigit() for char in password):
        return {'error': _('password_must_contain_digit')}
    if not any(char.isupper() for char in password):
        return {'error': _('password_must_contain_uppercase')}
    if not any(char.islower() for char in password):
        return {'error': _('password_must_contain_lowercase')}
    if not any(char in ['$', '@', '#', '%', '&', '*', '(', ')', '-', '_', '+', '='] for char in password):
        return {'error': _('password_must_contain_special_char')}
    # The password is valid
    return None

def send_email(request, subject: str, recipients: list, template_path: str, template_vars: Dict= {}) -> bool:
    """
    Generic function to send emails.
    
    Args:
        request: The incoming Pyramid request object.
        subject: Subject of the email.
        recipients: List of email addresses to send the email to.
        template_path: Path to the email body template.
        template_vars: Variables to be used in the template.
        
    Returns:
        bool: True if email is sent successfully, otherwise False.
    """
    text_body = render_to_response(template_path, request=request, value={**template_vars, "textual":True}).text
    for i in range(5, 1, -1):
        text_body = text_body.replace("\n"*i, "\n")
    text_body = text_body.replace("<!DOCTYPE html>\n", "").replace("\n\n\n\n","\n").replace("\n\n\n","\n").replace("\n\n","\n")
    html_body = render_to_response(template_path, request=request, value={**template_vars, "textual":False}).body
    sender = request.registry.settings['mail.default_sender']
    message = Message(
        subject=subject,
        sender=sender,
        recipients=recipients,
        body=Attachment(content_type='text/plain; charset=utf-8', data=text_body),
        html=Attachment(content_type='text/html; charset=utf-8', data=html_body)
    )
    log.debug(f"Email {subject} is prepared and will be sent to {recipients} from {sender} and contains {text_body}")

    mailer = request.registry['mailer']
    status = mailer.send(message) # Remember the message is not sent until the transaction is committed
    
    if status is None:
        log.error(f"Error while preparing sending email {subject} to {recipients}")
        return False
    else:
        log.info(f"Email {subject} will be sent to {recipients}")
        return True


def generate_math_challenges(request: Request)->Dict[str, str]:
    """Generate four simple math challenges.
    Args:
        request (pyramid.request.Request): the request
    return:
        dict: A dictionary containing the math challenges and their solutions.
    """
    challenges = {}
    numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    number_dict = {word: index for index, word in enumerate(numbers)}
    localizer = get_localizer(request)
    for label in ["A", "B", "C", "D"]:
        num1 = random.randint(1, 9)
        str_num1 = localizer.translate(_(num1))
        num2 = random.randint(1, 9)
        str_num2 = localizer.translate(_(num2))
        num3 = random.randint(1, 9)
        str_num3 = localizer.translate(_(num3))
        str_times = localizer.translate(_("times"))
        str_plus = localizer.translate(_("plus"))
        challenge_str = f"{str_num1} {str_times} {str_num2} {str_plus} {str_num3}"
        challenge_solution = num1 * num2 + num3
        challenges[label] = (challenge_str, challenge_solution)
    return challenges

def get_candidature_by_oid(oid, request):
    """Get the candidature by its oid.
    Args:
        oid (str): the oid of the candidature
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature
    """
    candidatures = get_candidatures(request)
    return candidatures[oid] if oid in candidatures else None

def get_candidature_from_request(request: Request)->Candidature:
    """Get the candidature from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature
    """
    encrypted_oid = request.params.get("oid")

    decrypted_oid, seed = decrypt_oid(encrypted_oid, Candidature.SEED_SIZE, request.registry.settings['session.secret'])
    candidature = get_candidature_by_oid(decrypted_oid, request)
    if seed != candidature.seed:
        raise Exception("Seed mismatch")
    return candidature


def generate_key(secret:str)->bytes:
    """Generate a key from the secret.
    Args:
        secret (str): The secret to use to generate the key
    Returns:
        bytes: The key
    """    
    sha256 = hashlib.sha256()
    sha256.update(secret.encode())
    return sha256.digest()


def decrypt_oid(encrypted_oid: str, seed_size:int, secret:str)->[str,str]:
    """ Function to decrypt the OID using the SECRET and return the decrypted OID
    Args:
        encrypted_oid (str): The encrypted OID
        secret (str): The secret to use to decrypt the OID
    Returns:
        str: The decrypted OID
        str: The seed
    """
    fernet = Fernet(secret)
    decoded_encrypted_oid = base64.urlsafe_b64decode(encrypted_oid)
    decrypted_message = fernet.decrypt(encrypted_oid).decode()
    index = len(decrypted_message)-seed_size
    return decrypted_message[:index], decrypted_message[index:]


def encrypt_oid(oid, seed, secret) -> str:
    """ Function to encrypt the OID using the SECRET and return the encrypted OID
    Args:
        oid (str): The OID to encrypt
        seed_size (int): The seed size
        secret (str): The secret to use to encrypt the OID
    Returns:
        str: The encrypted OID
    """
    concatenated_string = oid + seed
    fernet = Fernet(secret)
    encrypted_message = fernet.encrypt(concatenated_string.encode())
    encoded_encrypted_message = base64.urlsafe_b64encode(encrypted_message).decode()
    return encrypted_message

def random_voters(request: Request)->list[tuple[str, str]]:
    """Randomly select 3 voters to validate the candidate's personal data.
    For this, retrieve from LDAP the list of members who are cooperators, then
    randomly choose 3 if there are enough; otherwise, offer what is available..
    Args:
        request (pyramid.request.Request): the request
    Returns:
        list: the list of voters as (email, fullsurname)
    """
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login=f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
    conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True)
    conn.search(LDAP_BASE_DN, '(employeeType=cooperator)', attributes=['cn'])
    voters = []
    for entry in conn.entries:
        voters.append(entry.cn.value)
    random.shuffle(voters) # Shuffle the list of voters
    voters = voters[:3] # Return the first 3 voters
    voters_info = []
    for voter in voters:
        conn.search(LDAP_BASE_DN, '(cn={})'.format(voter), attributes=['mail'])
        voter_email = conn.entries[0].mail.value
        voter_fullsurname = conn.entries[0].sn.value
        voters_info.append((voter_email, voter_fullsurname))
    return voters_info

def register_user_to_ldap(request, candidature, password):
    """
    Register a user to the LDAP directory.
    
    Args:
        request (pyramid.request.Request): the request.
        candidature (Candidature): the candidature of the user to register.
    
    Returns:
        dict: a dictionary containing the result of the registration.
    """
    
    # First, check if the pseudonym is unique
    pseudonym = candidature.pseudonym
    error = is_valid_unique_pseudonym(pseudonym)
    if error:
        return error

    # Continue to register the user to LDAP
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login=f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
    log.debug(f"LDAP Connection{LDAP_LOGIN=},{LDAP_OU=},{LDAP_BASE_DN=},{LDAP_PASSWORD=},{LDAP_SERVER=}")  
    conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True)

    # DN for the new entry
    dn = f"uid={pseudonym},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"uid={pseudonym},{LDAP_BASE_DN}"
    # Attributes for the new user
    attributes = {
        'objectClass': ['top', 'inetOrgPerson'],  # Adjust this based on your LDAP schema
        'uid': pseudonym,
        'mail': candidature.email,
        'userPassword': password,
        'cn': pseudonym,
        'employeeNumber': candidature.oid, # Use the oid as employeeNumber
        'employeeType': candidature.type.name, # Use the type as employeeType
    }
    log.debug(f"LDAP Add {dn=},{attributes=}, {password=}")
    # Add the new user to LDAP
    try:
        success = conn.add(dn, attributes=attributes)
    except Exception as e:
        log.error(f"Error while adding user {pseudonym} to LDAP: {e}")
        success = False
    if success:
        return {'status': 'success', 'message': _('registration_successful')}
    else:
        return {'status': 'failure', 'message': _('registration_failed')}
