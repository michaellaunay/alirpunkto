# Definition of the functions used in the project
# author: Michaël Launay
# date: 2023-09-30

from pyramid.request import Request
from .models.candidature import Candidature, CandidatureStates, Candidatures, CandidatureTypes, VotingChoice
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
from .models import appmaker

def get_candidatures(request)->Candidatures:
    """Get the candidatures from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidatures: the candidatures
    """
    conn = get_connection(request)
    root = appmaker(conn.root())
    # Create the candidatures singletons if it doesn't exist
    if 'candidatures' not in root:
        root['candidatures'] = Candidatures.get_instance(zodb=conn)
    return root['candidatures']

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
    ldap_login=f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}" if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}" # define the user to authenticate
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
        tuple: A tuple containing the string math challenge and the solution in integer.
    """
    numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    number_dict = {word: index for index, word in enumerate(numbers)}
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

    return (f"({str_num1} + {str_num2}) * ({str_num3} + {str_num4}) + {str_num5}",
        (number_dict[num1] + number_dict[num2]) * (number_dict[num3] + number_dict[num4]) + number_dict[num5])

def get_candidature_by_oid(oid, request):
    """Get the candidature by its oid.
    Args:
        oid (str): the oid of the candidature
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature
    """
    candidatures = get_candidatures(request)
    return candidatures[oid]

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
    decrypted_message = fernet.decrypt(encrypted_oid).decode()
    return decrypted_message[:seed_size], decrypted_message[seed_size:]


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
    return encrypted_message