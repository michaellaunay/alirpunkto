# Definition of the functions used in the project
# author: Michaël Launay
# date: 2023-09-30

from typing import Dict, Union
import datetime
from pyramid.request import Request
from alirpunkto.models.user_datas import (
    PersistentUsers,
    PersistentUserDatas,
    EmailSendStatus,
    UserDatas,
    UserTypes
)
from .models.candidature import (
    Candidature,
    CandidatureStates,
)
from pyramid_mailer.message import Message, Attachment
from pyramid_zodbconn import get_connection
from pyramid.path import AssetResolver
from .constants_and_globals import (
    _,
    ADMIN_LOGIN,
    ADMIN_PASSWORD,
    ADMIN_EMAIL,
    LDAP_SERVER,
    LDAP_OU,
    LDAP_BASE_DN,
    LDAP_LOGIN,
    LDAP_PASSWORD,
    LDAP_ADMIN_OID,
    EUROPEAN_LOCALES,
    DEFAULT_NUMBER_OF_VOTERS,
    MIN_PSEUDONYM_LENGTH,
    MAX_PSEUDONYM_LENGTH,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    pseudonym_pattern,
    log,
    SPECIAL_CHARACTERS
)
from pyramid.i18n import get_localizer
from ldap3 import Server, Connection, ALL, MODIFY_ADD
from validate_email import validate_email
from pyramid.renderers import render_to_response
import random
import hashlib
from cryptography.fernet import Fernet
import base64
from .models.users import User

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

def get_candidatures(request)->PersistentUsers:
    """Get the candidatures from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidatures: the candidatures
    """
    conn = get_connection(request)
    return PersistentUsers.get_instance(connection=conn)

def get_members(request)->PersistentUsers:
    """Get the persistent users from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        PersistentUsers: the persistent users
    """
    conn = get_connection(request)
    return PersistentUsers.get_instance(connection=conn)

def get_unsecure_ldap_connection() -> Connection:
    """Get an unsecure LDAP connection.
    Returns:
        Connection: the unsecure LDAP connexion
    """
    # define an unsecure LDAP server, requesting info on DSE and schema
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login=(f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}"
        if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
    )# define the user to authenticate
    # define an unsecure LDAP connection, using the credentials above
    conn = Connection(
        server,
        ldap_login,
        LDAP_PASSWORD,
        auto_bind=True
    )
    return conn

def get_member_by_mail(email: str) -> Union[Dict[str, str], None]:
    """Get the member from LDAP by its mail.
    Args:
        email (str): the mail of the member
    Returns:    
        dict: the member
        None: if the member is not found
    """
    conn = get_unsecure_ldap_connection()
    # search for the user in the LDAP directory
    conn.search(
        LDAP_BASE_DN,
        f'(mail={email.strip()})',
        attributes=['cn', 'uid', 'isActive', 'employeeType']
    )
    return conn.entries

def is_not_a_valid_email_address(email:str, check_mx:bool=True)->Union[Dict[str, str], None]:
    """Check if the email is not a valid email address.
    Args:
        email (str): the email to check
        check_mx (bool): check the mx record
    Returns:
        error: the error if the email is not valid
        None: if the email is valid
    """
    try:
        if not validate_email(email, check_mx=check_mx):
            return {'error': _('invalid_email')}
    except Exception as e:
        log.error(f"Error while validating email {email}: {e}")
        return {'error': _('connection_error')}
    return None

def is_valid_email(email, request):
    """Check if the email is valid and not used in LDAP.

    Args:
        email (str): the email to check
        request (pyramid.request.Request): the request

    Returns:
        error: the error if the email is not valid
        None: if the email is valid
    """
    if err := is_not_a_valid_email_address(email):
        return err
    try:
        # Verify that the email is not already registered in candidatures
        candidatures = get_candidatures(request)
        for candidature in candidatures.values():
            if candidature.email == email and candidature.state != CandidatureStates.REFUSED:
                return {'error': _('email_allready_exist')}
        # Verify that the email is not already registered in LDAP
        entries = get_member_by_mail(email)
        if len(entries) != 0:
            # If already registered, display an error message
            return {'error': _('email_allready_exist')}
    # The email is valid and not already used
    except:
        log.error(f"Error while checking email {email} in LDAP with {LDAP_SERVER=}, {LDAP_LOGIN=}, {LDAP_OU=}, {LDAP_BASE_DN=}")
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
        return {'error': _('invalid_pseudonym', {
                "MIN_PSEUDONYM_LENGTH":MIN_PSEUDONYM_LENGTH,
                "MAX_PSEUDONYM_LENGTH":MAX_PSEUDONYM_LENGTH
            })}

    if len(pseudonym) < MIN_PSEUDONYM_LENGTH:
        return {
            'error': _('pseudonym_too_short'),
            'error_details':_("pseudonym_minimum_length",
                {"MIN_PSEUDONYM_LENGTH":MIN_PSEUDONYM_LENGTH})
        }
    if len(pseudonym) > MAX_PSEUDONYM_LENGTH:
        return {
            'error': _('pseudonym_too_long'),
            'error_details':_("pseudonym_maximum_length",
                {"MAX_PSEUDONYM_LENGTH":MAX_PSEUDONYM_LENGTH})
        }
    # define an unsecure LDAP server, requesting info on DSE and schema
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login= (f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}"
        if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
        ) # define the user to authenticate
    conn = Connection(
        server,
        ldap_login,
        LDAP_PASSWORD,
        auto_bind=True
    ) # define an unsecure LDAP connection, using the credentials above
    # Verify that the pseudonym is not already registered
    conn.search(
        LDAP_BASE_DN,
        f"(cn={pseudonym})",
        attributes=['cn']
    ) # search for the user in the LDAP directory
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
        return {
            'error': _('password_too_short'),
            'error_details':_("password_minimum_length",
            mapping={'password_minimum_length':MIN_PASSWORD_LENGTH})
        }
    if len(password) > MAX_PASSWORD_LENGTH:
        return {
            'error': _('password_too_long'),
            'error_details':_("password_maximum_length",
            mapping={'password_maximum_length':MAX_PASSWORD_LENGTH})
        }
    if not any(char.isdigit() for char in password):
        return {'error': _('password_must_contain_digit')}
    if not any(char.isupper() for char in password):
        return {'error': _('password_must_contain_uppercase')}
    if not any(char.islower() for char in password):
        return {'error': _('password_must_contain_lowercase')}
    if not any(
        char in SPECIAL_CHARACTERS
        for char in password
    ):
        return {'error': _('password_must_contain_special_char')}
    # The password is valid
    return None

def send_email(
        request:Request,
        subject:str,
        recipients:list,
        template_path:str,
        template_vars:Dict= {}
    ) -> bool:
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
    text_body = render_to_response(
        template_path,
        request=request,
        value={**template_vars, "textual":True}
    ).text
    for i in range(5, 1, -1):
        text_body = text_body.replace("\n"*i, "\n")
    text_body = text_body.replace("<!DOCTYPE html>\n", "") \
                     .replace("\n\n\n\n", "\n") \
                     .replace("\n\n\n", "\n") \
                     .replace("\n\n", "\n")
    html_body = render_to_response(
        template_path,
        request=request,
        value={**template_vars, "textual":False}
    ).body
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
        str_num1 = localizer.translate(_(numbers[num1]))
        num2 = random.randint(1, 9)
        str_num2 = localizer.translate(_(numbers[num2]))
        num3 = random.randint(1, 9)
        str_num3 = localizer.translate(_(numbers[num3]))
        str_times = localizer.translate(_("times"))
        str_plus = localizer.translate(_("plus"))
        str_plus_prefix = localizer.translate(_("plus_prefix"))
        challenge_str = f"{str_num1} {str_times} {str_num2}{str_plus_prefix}{str_plus} {str_num3}"
        challenge_solution = num1 * num2 + num3
        challenges[label] = (challenge_str, challenge_solution)
    return challenges

def get_candidature_by_oid(
        oid:str,
        request:Request
    ) -> Candidature:
    """Get the candidature by its oid.
    Args:
        oid (str): the oid of the candidature
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature or None if not found or not a Candidature
    """
    candidatures = get_candidatures(request)
    candidature = candidatures[oid] if oid in candidatures else None
    if not isinstance(candidature, Candidature):
        candidature = None
    return candidature

def get_member_by_oid(
        oid:str,
        request:Request
    ) -> PersistentUserDatas:
    """Get the persistent user by its oid.
    Args:
        oid (str): the oid of the persistent user
        request (pyramid.request.Request): the request
    Returns:
        PersistentUser: the persistent user or None if not found or not a PersistentUser
    """
    candidatures = get_candidatures(request)
    user = candidatures[oid] if oid in candidatures else None
    if not isinstance(user, PersistentUserDatas):
        user = None
    return user

def append_persistent_user(
        persistent_user: PersistentUserDatas,
        request: Request):
    """Append the persistent user to the list of persistent users.
    Args:
        persistent_user (PersistentUser): the persistent user
        request (pyramid.request.Request): the request
    """
    persistent_users = get_members(request)
    persistent_users[persistent_user.oid] = persistent_user

def update_member_from_ldap(
        oid: str,
        request: Request
    ) -> Union[PersistentUserDatas, None]:
    """Update the persistent users from LDAP.
    Args:
        oid (str): the oid of the user
        request (pyramid.request.Request): the request
    Returns:
        PersistentUser: the persistent user
        None: if not found in ldap
    """
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login = (f"{LDAP_LOGIN},"
                  f"{(LDAP_OU + ',') if LDAP_OU else ''}"
                  f"{LDAP_BASE_DN}"
    )
    try:
        conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True)
    except Exception as e:
        log.error(f"Error while connecting to LDAP: {e}")
        return None
    # Extend the list of attributes retrieved to include all those added during registration
    try:
        conn.search(
            LDAP_BASE_DN,
            f'(uid={oid})',
            attributes=['cn', 'mail', 'employeeType', 'sn', 'uid', 'userPassword', 'employeeNumber', 'isActive', 'gn', 'nationality', 'birthdate', 'preferredLanguage', 'secondLanguage']
        )
        if len(conn.entries) == 0:
            log.warning(f"User {oid} not found in LDAP")
            return None
    except Exception as e:
        log.error(f"Error while searching for user {oid} in LDAP: {e}")
        return None
    user_entry = conn.entries[0]
    persistent_user_datas = get_member_by_oid(oid, request)

    new_email = user_entry.mail.value.strip() if hasattr(user_entry, 'mail') else None
    new_pseudonym = user_entry.cn.value.strip() if hasattr(user_entry, 'cn') else None
    new_type = UserTypes[user_entry.employeeType.value.strip()] if hasattr(user_entry, 'employeeType') else None
    new_fullname = user_entry.gn.value.strip() if hasattr(user_entry, 'gn') else None
    new_nationality = user_entry.nationality.value.strip() if hasattr(user_entry, 'nationality') else None
    new_birthdate = datetime.strptime(user_entry.birthdate.value, "%Y-%m-%d") if hasattr(user_entry, 'birthdate') else None
    new_preferred_language = user_entry.preferredLanguage.value.strip() if hasattr(user_entry, 'preferredLanguage') else None
    new_second_language = user_entry.secondLanguage.value.strip() if hasattr(user_entry, 'secondLanguage') else None

    log.debug(f"Update PersistentUser {oid} with ldap informations")
    if not persistent_user_datas:
        log.debug(f"Create PersistentUser {oid} with informations found in LDAP with {new_email=}, {new_pseudonym=}, {new_type=}, {new_fullname=}, {new_nationality=}, {new_birthdate=}, {new_preferred_language=}, {new_second_language=}")
        datas = UserDatas(
            fullname=new_fullname,
            fullsurname = new_fullname,
            nationality = new_nationality,
            birthdate = new_birthdate,
            password = None,
            password_confirmation = None,
            lang1 = new_preferred_language,
            lang2 = new_second_language,
            role = new_type
        )
        persistent_user_datas = PersistentUserDatas(
            email=new_email,
            pseudonym=new_pseudonym,
            oid=oid,
            data=datas
        )
        append_persistent_user(persistent_user_datas, request)
    else :
        # Update the persistent_user_datas object with the data retrieved from LDAP
        if new_email and persistent_user_datas.email != new_email:
            log.debug(f"Update PersistentUser {oid} with new email {new_email}")
            persistent_user_datas.email = new_email
        if new_pseudonym and persistent_user_datas.pseudonym != new_pseudonym:
            log.debug(f"Update PersistentUser {oid} with new pseudonym {new_pseudonym}")
            persistent_user_datas.pseudonym = new_pseudonym
        if new_type and persistent_user_datas.type != new_type:
            log.debug(f"Update PersistentUser {oid} with new type {new_type}")
            persistent_user_datas.type = new_type
        # Add additional fields for cooperators
        if new_fullname and persistent_user_datas.data.fullname != new_fullname:
            log.debug(f"Update PersistentUser {oid} with new fullname {new_fullname}")
            persistent_user_datas.data.fullname = new_fullname
        if new_nationality and persistent_user_datas.data.national != new_nationality:
            log.debug(f"Update PersistentUser {oid} with new nationality {new_nationality}")
            persistent_user_datas.data.nationality = new_nationality
        if new_birthdate and persistent_user_datas.data.birthdate != new_birthdate:
            log.debug(f"Update PersistentUser {oid} with new birthdate {new_birthdate}")
            persistent_user_datas.data.birthdate = new_birthdate
        if new_preferred_language and persistent_user_datas.data.lang1 != new_preferred_language:
            log.debug(f"Update PersistentUser {oid} with new preferred language {new_preferred_language}")
            persistent_user_datas.data.lang1 = new_preferred_language
        if new_second_language and persistent_user_datas.data.lang2 != new_second_language:
            log.debug(f"Update PersistentUser {oid} with new second language {new_second_language}")
            persistent_user_datas.data.lang2 = new_second_language
    return persistent_user_datas

def get_candidature_from_request(request: Request)->Candidature:
    """Get the candidature from the request.
    Args:
        request (pyramid.request.Request): the request
    Returns:
        Candidature: the candidature
    """
    encrypted_oid = request.params.get("oid")

    decrypted_oid, seed = decrypt_oid(
        encrypted_oid,
        Candidature.SEED_SIZE,
        request.registry.settings['session.secret']
    )
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

def decrypt_oid(encrypted_oid: str, seed_size: int, secret: str) -> [str, str]:
    """Decrypt the OID using the SECRET and return the decrypted OID and seed.

    Args:
        encrypted_oid (str): The encrypted OID.
        seed_size (int): The size of the seed.
        secret (str): The secret to use to decrypt the OID.

    Returns:
        tuple: The decrypted OID and the seed.
    """
    fernet = Fernet(secret)
    decoded_encrypted_oid = base64.urlsafe_b64decode(encrypted_oid)
    decrypted_message = fernet.decrypt(decoded_encrypted_oid).decode()
    index = len(decrypted_message) - seed_size
    return decrypted_message[:index], decrypted_message[index:]

def encrypt_oid(oid: str, seed: str, secret: str) -> str:
    """Encrypt the OID using the SECRET and return the encrypted OID.

    Args:
        oid (str): The OID to encrypt.
        seed (str): The seed.
        secret (str): The secret to use to encrypt the OID.

    Returns:
        str: The encrypted OID.
    """
    concatenated_string = oid + seed
    fernet = Fernet(secret)
    encrypted_message = fernet.encrypt(concatenated_string.encode())
    encoded_encrypted_message = base64.urlsafe_b64encode(
        encrypted_message).decode()
    
    return encoded_encrypted_message

from typing import List, Dict

def get_potential_voters(conn: Connection) -> List[Dict[str, str]]:
    """Fetch potential voters from LDAP.

    Args:
        conn (Connection): The LDAP connection object.

    Returns:
        list: List of potential voters (uid, cn, mail, sn).
    """
    filter_str = '(&(employeeType=cooperator)(cn=*)(mail=*))'
    conn.search(LDAP_BASE_DN, filter_str, attributes=['uid', 'cn', 'mail', 'sn'])
    return conn.entries

def get_admin_user()->  User:
        """return the admin User from the sttings.
        Args:
            request (pyramid.request.Request): the request
        Returns:
            User: The admin from the settings
        """
        name = ADMIN_LOGIN
        mail = ADMIN_EMAIL
        oid = LDAP_ADMIN_OID
        admin_user = User(name, mail, oid)
        return admin_user

def random_voters(request: Request) -> List[Dict[str, str]]:
    """
    Randomly select the number of voters defined in settings to validate the
    candidate's personal data.
    
    Args:
        request (pyramid.request.Request): The request.

    Returns:
        list: A list of voters in the format: 
            [{'cn': 'name', 'sn': 'surname', 'mail': 'email'}, ...]
    """
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login = (f"{LDAP_LOGIN},"
                  f"{(LDAP_OU + ',') if LDAP_OU else ''}"
                  f"{LDAP_BASE_DN}"
    )
    # Get the number of voters from the settings
    try:
        number_of_voters = int(request.registry.settings['number_of_voters'])
    except:
        number_of_voters = DEFAULT_NUMBER_OF_VOTERS
        log.warning(f"Use {DEFAULT_NUMBER_OF_VOTERS=} "
            "as number of voters due to exception.")
    with Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) as conn:
        potential_voters = get_potential_voters(conn)
        random.shuffle(potential_voters)
        selected_voters = potential_voters[:number_of_voters]

        voters = [
            {
                'uid': voter.uid.value,
                'cn': voter.cn.value,
                'sn': voter.sn.value if hasattr(voter, "sn") else voter.cn.value,
                'mail': voter.mail.value
            }
            for voter in selected_voters
        ]

        # If there are fewer than number_of_voters voters, add the admin
        if len(voters) < number_of_voters:
            voters.append(
                {
                    'uid': LDAP_ADMIN_OID,
                    'cn': ADMIN_LOGIN,
                    'sn': 'Administrator',
                    'mail': ADMIN_EMAIL
                }
            )

        return voters[:number_of_voters]  # Ensure only top number_of_voters are returned

def get_oid_from_pseudonym(
    pseudonym: str,
    request: Request
    ) -> Union[str, None]:
    """Get the oid from the pseudonym and ldap.

    Args:
        pseudonym (str): the pseudonym
        request (pyramid.request.Request): the request

    Returns:
        str: the oid, None if not found
    """
    #verify pseudonym is valid
    pseudonym = pseudonym.strip()
    if not pseudonym_pattern.match(pseudonym):
        return None
    server = Server(LDAP_SERVER, get_info=ALL)
    ldap_login = f"{LDAP_LOGIN},{LDAP_OU if LDAP_OU else ''},{LDAP_BASE_DN}"
    while ',,' in ldap_login:
        ldap_login = ldap_login.replace(',,', ',')
    with Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True) as conn:
        conn.search(
            LDAP_BASE_DN,
            '(cn={})'.format(pseudonym),
            attributes=['employeeNumber']
        ) # search for the user in the LDAP directory
        if len(conn.entries) == 0:
            return None
        user_entry = conn.entries[0]
        return user_entry.employeeNumber.value

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
    ldap_login=(f"{LDAP_LOGIN},{LDAP_OU},{LDAP_BASE_DN}"
        if LDAP_OU else f"{LDAP_LOGIN},{LDAP_BASE_DN}"
    )
    log.debug(
        f"LDAP Connection{LDAP_LOGIN=},{LDAP_OU=},{LDAP_BASE_DN=},"
        f"{LDAP_PASSWORD=},{LDAP_SERVER=}"
    )
    conn = Connection(server, ldap_login, LDAP_PASSWORD, auto_bind=True)

    # DN for the new entry
    dn = (f"uid={candidature.oid},{LDAP_OU},{LDAP_BASE_DN}"
        if LDAP_OU else f"uid={candidature.oid},{LDAP_BASE_DN}"
    )
    # Attributes for the new user
    attributes = {
        # Adjust this based on your LDAP schema
        'objectClass': ['top', 'inetOrgPerson', 'alirpunktoPerson'],
        'uid': candidature.oid,
        'mail': candidature.email,
        'userPassword': password,
        'sn': (
            candidature.data.fullsurname
                if candidature.type == UserTypes.COOPERATOR
                else pseudonym
        ), # sn is obligatory
        'cn': pseudonym, # Use the pseudonym as commonName
        'employeeNumber': candidature.oid, # Use the oid as employeeNumber
        'employeeType': candidature.type.name, # Use the type as employeeType,
         # Use the fullsurname as sn
        "isActive": "True",
    }
    if candidature.type == UserTypes.COOPERATOR:
        # Add full name to inetOrgPerson attribute
        #@TODO conforter
        attributes['gn'] = candidature.data.fullname
        #@TODO check country code is less of 3 chars
        attributes["nationality"] = candidature.data.nationality
        attributes["birthdate"] = candidature.data.birthdate.strftime("%Y%m%d%H%M%SZ")
        #@TODO check language code
        attributes["preferredLanguage"] = candidature.data.lang1
        attributes["secondLanguage"] = candidature.data.lang2
    log.debug(f"LDAP Add {dn=},{attributes=}, {password=}")
    # Add the new user to LDAP
    try:
        success = conn.add(dn, attributes=attributes)
        if success:
            match candidature.type:
                case UserTypes.COOPERATOR:
                    group_dn = ("cn=cooperatorsGroup,"
                                f"{f'ou={LDAP_OU},' if LDAP_OU else ''}"
                                f"{LDAP_BASE_DN}"
                    )
                    conn.modify(group_dn, {'uniqueMember': [(MODIFY_ADD, [dn])]})
                case UserTypes.ORDINARY:
                    group_dn = ("cn=ordinaryMembersGroup,"
                                f"{f'ou={LDAP_OU},' if LDAP_OU else ''}"
                                f"{LDAP_BASE_DN}"
                    )
                    conn.modify(group_dn, {'uniqueMember': [(MODIFY_ADD, [dn])]})
                case _:
                     log.error(f"Error while adding user {pseudonym} "
                               f"to a LDAP group : group for {candidature.type} is not coded")

            # Check if group addition was successful
            if not conn.result['description'] == 'success':
                log.error(f"Error while adding user {pseudonym} to group {group_dn}: {conn.result}")
           
    except Exception as e:
        log.error(f"Error while adding user {pseudonym} to LDAP: {e}")
        success = False
    if success:
        return {'status': 'success', 'message': _('registration_successful')}
    else:
        log.error(f"Error while adding user {pseudonym} to LDAP : {conn.result}")
        return {'status': 'error', 'message': _('registration_failed')}

def is_admin(username:str, password:str)-> bool:
    """
    Determines if the provided username and password match the credentials of the administrator.

    This function checks if the given username and password combination is the same as that of the
    administrator.

    Args:
    username (str): The username to be checked.
    password (str): The password corresponding to the username.

    Returns:
    bool: Returns True if the provided username and password match the administrator's credentials, 
    otherwise returns False.
    """
    return (username.strip(), password.strip())== (ADMIN_LOGIN.split("=")[-1], ADMIN_PASSWORD)

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
        log.error(
            f"Error while resolving locale file for {lang} for {pattern_path}"
            f", fallback to en."
        )
        resolver = ar.resolve(pattern_path.format(lang="en"))
    return resolver

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

# @TODO generalize this function to PersistentUserDatas
def send_candidature_state_change_email(request: Request,
    candidature: PersistentUserDatas,
    sending_function_name : str,
    template_name : str = None,
    subject:str = None) -> Dict:
    """Send the candidature state change email to the candidate.
    Args:
        request (pyramid.request.Request): the request
        candidature (PersistentUserDatas): the candidature
        sending_function_name (str): the name of the function that sends the email
        template_name (str): the name of the template to use or None to use the default template
        subject (str): the subject of the email or None to use the default subject
    Returns:
        dict: the result of the email sending
    """
    template_name = (template_name
        if template_name
        else 'locale/{lang}/LC_MESSAGES/candidature_state_change.pt'
    )
    template_path = get_local_template(request, template_name).abspath()
    localizer = get_localizer(request)
    subject = (subject if subject
        else localizer.translate(_('email_candidature_state_changed'))
    )
    email = candidature.email
    seed = candidature.email_send_status_history[-1].seed

    # Prepare the necessary information for the email
    parameter = encrypt_oid(
        candidature.oid,
        seed,
        request.registry.settings['session.secret']
    )
  
    url = request.route_url('register', _query={'oid': parameter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    #We don't have user yet so we use the email parts befor the @ or pseudonym if it exists
    user = (candidature.pseudonym if hasattr(candidature, "pseudonym")
            else email.split('@')[0]
    )
    
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
        success = send_email(
            request,
            subject,
            [email],
            template_path,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
    
    if success:
        candidature.add_email_send_status(
            EmailSendStatus.SENT, sending_function_name)
        return {'success': True}
    else:
        candidature.add_email_send_status(
            EmailSendStatus.ERROR, sending_function_name)
        return {'error': _('email_not_sent')}

def send_email_to_member(request: Request,
    member: PersistentUserDatas,
    sending_function_name,
    template_name,
    subject_msgid,
    view_name) -> Dict:
    """Send an email to the member.
    Args:
        request (pyramid.request.Request): the request
        member (PersistentUserDatas): the member
        sending_function_name (str): the name of the function that sends the email
        template_name (str): the name of the template to use
        subject_msgid (str): the msgid of the email subject
        view_name (str): the name of the view to use in the email
    Returns:
        dict: the result of the email sending
    """

    template_path = get_local_template(request, template_name).abspath()
    localizer = get_localizer(request)
    subject = localizer.translate(_(subject_msgid))
    email = member.email
    seed = member.email_send_status_history[-1].seed

    # Prepare the necessary information for the email
    parameter = encrypt_oid(
        member.oid,
        seed,
        request.registry.settings['session.secret']
    )
  
    url = request.route_url(view_name, _query={'oid': parameter})
    site_url = request.route_url('home')
    site_name = request.registry.settings.get('site_name')
    
    template_vars = {
        'page_with_oid': url,
        'site_url': site_url,
        'site_name': site_name,
        'member': member.data,
    }
    
    # Use the send_email from utils.py
    try:
        # Stack email sending action to be executed at commit
        success = send_email(
            request,
            subject,
            [email],
            template_path,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
    
    if success:
        member.add_email_send_status(
            EmailSendStatus.SENT, sending_function_name)
        return {'success': True}
    else:
        member.add_email_send_status(
            EmailSendStatus.ERROR, sending_function_name)
        return {'error': _('email_not_sent')}

def send_validation_email(
        request: Request,
        candidature: 'Candidature'
    ) -> bool:
    """
    Send the validation email to the candidate.
    
    Args:
        request: The request object.
        candidature: The candidature object.
        
    Returns:
        bool: True if the email is successfully sent, False otherwise.
    """
    template_path = get_local_template(
        request,
        'locale/{lang}/LC_MESSAGES/check_email.pt'
    ).abspath()

    email = candidature.email # The email to send to.
    challenge = candidature.challenge # The math challenge for email validation.
    localizer = get_localizer(request)
    subject = localizer.translate(_('email_validation_subject'))
    seed = candidature.email_send_status_history[-1].seed
    parameter = encrypt_oid(
        candidature.oid,
        seed,
        request.registry.settings['session.secret']
    )
    
    url = request.route_url('register', _query={'oid': parameter})
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
        success = send_email(
            request,
            subject,
            [email],
            template_path,
            template_vars
        )
    except Exception as e:
        log.error(f"Error while sending email to {email} : {e}")
        success = False
    return success
