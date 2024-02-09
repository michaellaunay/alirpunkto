# Description: UserDatas model
# A UserDatas is an object that represents the user datas manage by the application.
# Creation date: 2024-02-06
# Author: Michaël Launay

from typing import Type, Tuple, List, Any, Optional, Dict, Iterator
from dataclasses import dataclass, fields
from persistent import Persistent
from persistent.mapping import PersistentMapping
from datetime import datetime
from pyramid.authorization import Allow, ALL_PERMISSIONS
from enum import Enum, unique
from uuid import uuid4
from ZODB.Connection import Connection
import transaction
import random
import string

# Constants
from alirpunkto.constants_and_globals import (
    _,
    log,
    SEED_LENGTH,
)

@unique
class UserStates(Enum) :
    """States of the user.
    """
    # Created: The user data set is in created mode.
    CREATED = "user_created_value"
    # Draft: The user data set is in draft mode.
    DRAFT = "user_draft_value"
    # Data modification requested: The user data set is in modification requested mode.
    DATA_MODIFICATION_REQUESTED = "user_datas_modification_request_value"
    # Data modified: The user data set is in modified mode.
    DATA_MODIFIED = "user_datas_modified_value"

    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the user state.
        Args:
            name: The name of the user state.
        Returns:
            The i18n id of the user state.
        """
        match name:

            case cls.CREATED.name :
                return "user_datas_states_created_name"
            case cls.DRAFT.name :
                return "user_datas_states_draft_name"
            case cls.DATA_MODIFICATION_REQUESTED.name :
                return "user_datas_modification_request_name"
            case cls.DATA_MODIFIED.name :
                return "user_datas_modified_name"
            case cls.CREATED.value :
                return "user_datas_states_created_value"
            case cls.DRAFT.name :
                return "user_datas_states_draft_value"
            case cls.DATA_MODIFICATION_REQUESTED.name :
                return "user_datas_modification_request_value"
            case cls.DATA_MODIFIED.name :
                return "user_datas_modified_value"
            case _ :
                # should never happen
                log.error(f"Unknown user state: {name}")
                return(f"name.lower()")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the user_datas states.
        Returns:
            The names of the user_datas states.
        """
        return UserStates.__members__.keys()

@unique
class EmailSendStatus(Enum):
    """Status of the email sent to the applicant or user.
    """
    #  In Preparation: The email is being prepared.
    IN_PREPARATION = "email_send_status_in_preparation_value"
    # Sent: The email has been sent.
    SENT = "email_send_status_sent_value"
    # Error: An error occured while sending the email.
    ERROR = "email_send_status_error_value"


@unique
class UserTypes(Enum) :
    """Types of user.
    """
    # Ordinary: The user is an ordinary member.
    ORDINARY = "user_types_ordinary_value"
    # Cooperator: The user is a cooperator member.
    COOPERATOR = "user_types_cooperator_value"
    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the user type.
        Args:
            name: The name of the user type.
        Returns:
            The i18n id of the user type.
        """
        match name:
            case cls.ORDINARY.name :
                return "user_types_ordinary"
            case cls.COOPERATOR.name :
                return "user_types_cooperator"
            case cls.ORDINARY.value :
                return "user_types_ordinary_value"
            case cls.COOPERATOR.value :
                return "user_types_cooperator_value"
            case _ :
                # should never happen
                log.error(f"Unknown user type: {name}")
                return(f"name.lower()")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the user types.
        Returns:
            The names of the user types.
        """
        return UserTypes.__members__.keys()

@unique
class UserRoles(Enum) :
    """Roles of users.
    """
    # None: No role.
    NONE = "user_role_none_value"
    # Ordinary: The user is an ordinary member.
    ORDINARY = "user_role_ordinary_value"
    # Cooperator: The user is a cooperator member.
    COOPERATOR = "user_role_cooperator_value"
    # Board:  The user is a board member.
    BOARD = "user_role_board_value"
    # MediationArbitrationCouncil: The user is a mediation arbitration
    #  council member.
    MEDIATION_ARBITRATION_COUNCIL = "user_role_mediation_arbitration_council_value"

    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the user role.
        Args:
            name: The name of the user role.
        Returns:
            The i18n id of the user role.
        """
        match name:
            case cls.NONE.name :
                return "user_roles_none"
            case cls.ORDINARY.name :
                return "user_roles_ordinary"
            case cls.COOPERATOR.name :
                return "user_roles_cooperator"
            case cls.BOARD.name :
                return "user_roles_board"
            case cls.MEDIATION_ARBITRATION_COUNCIL.name :
                return "user_roles_mediation_arbitration_council"
            case cls.ORDINARY.value :
                return "user_roles_ordinary_value"
            case cls.COOPERATOR.value :
                return "user_roles_cooperator_value"
            case cls.BOARD.value :
                return "user_roles_board_value"
            case cls.MEDIATION_ARBITRATION_COUNCIL.value :
                return "user_roles_mediation_arbitration_council_value"
            case _ :
                # should never happen
                log.error(f"Unknown user role: {name}")
                return(f"role_types_{name.lower()}")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the user roles.
        Returns:
            The names of the user roles.
        """
        return UserRoles.__members__.keys()

@dataclass
class UserDatasEvent:
    """An event.
    """
    datetime:datetime # the datetime of the event
    function_name:str # the name of the function that triggered the event
    value_before:Any # the value of the user_datas before the event
    value_after:Any # the value of the user_datas after the event
    seed:str # the seed of the user_datas at the moment of the event
    def __repr__(self):
        return f"<UserDatasEvent({self.datetime}, "\
                f"{self.function_name}, "\
                f"{self.value_before}, "\
                f"{self.value_after}, "\
                f"{self.seed})>"
    def __str__(self):
        value_before = self.value_before if not self.value_before is None else "None"
        value_after = self.value_after if not self.value_after is None else "None"
        return f"(datetime={self.datetime}, "\
                f"function_name={self.function_name}, "\
                f"value_before={value_before}, "\
                f"value_after={value_after}, "\
                f"seed={self.seed})"
    def __iter__(self):
        value_before = self.value_before if not self.value_before is None else "None"
        value_after = self.value_after if not self.value_after is None else "None"
        return iter(
            (
                self.datetime,
                self.function_name,
                value_before,
                value_after, self.seed
            )
        )

@dataclass
class EmailEvent:
    """An email send event
    """
    datetime:datetime # the datetime of the event
    state:EmailSendStatus # the state of the email
    function_name:str # the name of the function that triggered the event
    seed:str # the seed of the email send event

    def iter_attributes(self)-> Iterator[Tuple[str, Any]]:
        """Iterate over the attributes of the dataclass.
        Returns:
            Iterator[Tuple[str, Any]]: An iterator over the attributes of the
                dataclass.
        """
        for field in fields(self):
            yield field.name, getattr(self, field.name)


def random_string(
        length:int,
        chars:str = string.ascii_lowercase + string.digits
    ) -> str:
    """ Generate a random string of a given length.
    Could be overloaded for testing.
    Args:
        length: The length of the string.
        chars: The characters to use to generate the string.
    Returns:
        A random string.
    """
    return ''.join(random.choice(chars) for _ in range(length))

class UserDatasFunctions:
    """A class to store functions used by the UserDatas class.
    Easy to mook for testing.
    """
    func_now = datetime.now
    func_uuid = uuid4
    @staticmethod
    def now() -> datetime:
        """Get the current datetime.
        Returns:
            The current datetime.
        """
        return UserDatasFunctions.func_now()
    @staticmethod
    def uuid() -> str:
        """Get a unique identifier (UUID).
        Returns:
            A unique identifier (UUID).
        """
        return UserDatasFunctions.func_uuid()
    
@dataclass
class UserDatas:
    fullname: str
    fullsurname: str
    nationality: str
    birthdate: str
    password: str
    password_confirm: str
    lang1: str
    lang2: str
    is_ordinary_member: bool = False
    is_cooperator_member: bool = False
    is_board_member: bool = False
    is_member_of_mediation_arbitration_council: bool = False
    role: UserRoles = UserRoles.NONE

    def iter_attributes(self)-> Iterator[Tuple[str, Any]]:
        """Iterate over the attributes of the dataclass.
        Returns:
            Iterator[Tuple[str, Any]]: An iterator over the attributes of the
                dataclass.
        """
        for field in fields(self):
            yield field.name, getattr(self, field.name)

class PersistentUsers(PersistentMapping):
    """A mapping to store PersistentUserDatas in the ZODB.
    Coulb be used as a singleton if all calls are made through get_instance.
    """
    _instance = None

    @staticmethod
    def get_instance(connection:Connection = None) -> Type['PersistentUsers']:
        """Get the singleton instance. Not thread safe !
        Args:
            connection: The ZODB connection, could be change for testing.
        Returns:
            The singleton instance.
            This singleton instance is a mapping to store lists of PersistentUserDatas
            subtypes associated with one unique oid.
        Raises:
            TypeError: The connection argument must be an instance of 
                    ZODB.Connection.Connection
        """
        if PersistentUsers._instance is not None:
            #check if the zodb connexion is still alive then return the instance
            try:
                'test' in PersistentUsers._instance
            except Exception as e:
                log.error(f"Error while getting users instance: {e}")
                raise e
            return PersistentUsers._instance

        # Check if a ZODB is provided
        if not isinstance(connection, Connection):
            raise TypeError(
                "The connection argument must be an instance of "
                "ZODB.Connection.Connection"
            )

        # check if root exists
        root = connection.root()
        if 'users' not in root:
            connection.root()['users'] = PersistentUsers()
            transaction.commit()
        PersistentUsers._instance = connection.root()['users']
        return root['users']

    def __init__(self):
        """Constructor.
        """
        super().__init__()
        self._monitored_users = PersistentMapping()

    @property
    def monitored_users(self)-> PersistentMapping:
        """ Get the monitored users.
        A monitored user is a user that is not in DRAFT or
          APPROUVED or REFUSED state and needs to be monitored.
        For exemple, It could be necessary to send them a reminder email
          to the verifiers if the expiration date is approaching.
        Returns:
            The monitored users.DELETED
        """
        return self._monitored_users

    @property
    def users_emails(self)-> List[str]:
        """Retrieve the emails of all users.

        This method returns a list of email addresses from all users. 
        In future versions, this functionality might be enhanced with caching 
        and listeners to maintain updated and accurate values.

        Returns:
            List[str]: A list containing the emails of all users.
        """
        return [user.email for user in self.values()]


class PersistentUserDatas(Persistent):
    """A user_datas in the ZODB.
    """

    __acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]

    def __init__(self, data = None):
        """    Initialize a new PersistentUserDatas object.

        Args:
            data (Optional[Type]): Initial data for the user.
             Defaults to None.

        Attributes:
            _data (PersistentUserDatas): The data for the user.
            _modifications (List[UserDatasEvent]): A list to record
                modifications, each entry is a dataclass containing the
                datetime, the function name, the previous value, the new value.
            _state (UserStates): The current state of the user.
            _type (UserTypes or None): The type of the user.
            _email (str or None): The email associated with the user_datas.
            _oid (str): A unique object identifier.
            _seed (str): A random string used to generate the OID.
            _email_send_status_history (List[EmailEvent]): A list to
             record email send status history.
            _challenge (Tuple[str, int]): A tuple containing the string math
             challenge and the solution in integer.
            _pseudonym (str): The pseudonym of the user.
        Raises:
            RuntimeError: Raised if an instance already exists with same oid.

        """
        self._data = data
        self._voters = []
        self._state = UserStates.DRAFT
        self._type = None
        self._email = None
        self._votes = {}
        self._seed = None
        self._email_send_status_history = []
        self._challenge = None
        self._pseudonym = None
        # get a unique object id
        self._oid = PersistentUserDatas.generate_unique_oid()
        # get a random seed and record the creation
        self._modifications = []
        self._memorize_changes("__init__", None, self._state)

    def _memorize_changes(
        self, 
        function_name: Optional[str] = None, 
        previous_value: Optional[Any] = None, 
        new_value: Optional[Any] = None
        ) -> None:
        """Memorize changes to the user_datas and generate a new seed.
        
        Args:
            function_name (Optional[str]): The name of the function that
             triggered the change. Defaults to "_change_seed".
            previous_value (Optional[Any]): The previous value of the
             user_datas property. Defaults to None.
            new_value (Optional[Any]): The new value of the user_datas
            property. Defaults to None.
        """
        # Fallback to "_change_seed" if function_name is None
        function_name = function_name or "_change_seed"
        # Fallback to "None" if self._seed is None
        old_seed = self._seed or "None"

        self._seed = random_string(SEED_LENGTH) 

        event = UserDatasEvent(
            datetime=UserDatasFunctions.now(), 
            function_name=function_name,
            value_before=previous_value,
            value_after=new_value,
            seed=self._seed
        )

        self._modifications.append(event)
        self._p_changed = True  # Mark the object as changed

    @property
    def seed(self)-> str:
        """ Get the seed of the user.
        Returns:
            The seed of the user.
        """
        return self._seed

    @property
    def state(self)-> UserStates:
        """ Get the state of the user.
        Returns:
            The state of the user.
        """
        return self._state
    
    @state.setter
    def state(self, value:UserStates):
        """ Set the state of the user.

        Args:
            value (UserStates): The new state of the user.

        Raises:
            TypeError: The state must be an instance of UserStates.
        """
        if not isinstance(value, UserStates):
            raise TypeError(
                "The state must be an instance of UserStates."
            )
        
        old_state = self._state.name if self._state else "None"
        self._state = value
        self._memorize_changes("state", old_state, value.name)
    
    @property
    def type(self)-> UserTypes:
        """ Get the type of the user.
        Returns:
            The type of the user.
        """
        return self._type
    
    @type.setter
    def type(self, value:UserTypes):
        """ Set the type of the user.

        Args:
            value (UserTypes): The new type of the user.

        Raises:
            TypeError: The type must be an instance of UserTypes.
        """
        if not isinstance(value, UserTypes):
            raise TypeError(
                "The type must be an instance of UserTypes."
            )
        
        old_type = self._type.name if self._type else "None"
        self._type = value
        self._memorize_changes("type", old_type, value.name)

    @property
    def email(self)-> str:
        """ Get the email of the user.
        Returns:
            The email of the user.
        """
        return self._email
    
    @email.setter
    def email(self, value:str):
        """ Set the email of the user.

        Args:
            value (str): The new email of the user.

        Raises:
            TypeError: The email must be a string.
        """
        if not isinstance(value, str):
            raise TypeError("The email must be a string.")
        
        old_email = self._email if self._email else "None"
        self._email = value
        self._memorize_changes("email", old_email, value)

    @property
    def pseudonym(self)-> str:
        """ Get the pseudonym of the user.
        Returns:
            The pseudonym of the user.
        """
        return self._pseudonym
    
    @pseudonym.setter
    def pseudonym(self, value:str):
        """ Set the pseudonym of the user.

        Args:
            value (str): The new pseudonym of the user.

        Raises:
            TypeError: The pseudonym must be a string.
        """
        if not isinstance(value, str):
            raise TypeError("The pseudonym must be a string.")
        
        old_pseudonym = self._pseudonym if self._pseudonym else "None"
        self._pseudonym = value
        self._memorize_changes("pseudonym", old_pseudonym, value)

    @property
    def modifications(self)-> List[UserDatasEvent]:
        """ Get the modifications of the user.
        Returns:
            A copy of modifications of the user_datas as a list of
            user.
        """
        return self._modifications.copy()
    
    @property
    def oid(self)-> str:
        """ Get the oid of the user.
        Returns:
            The oid of the user.
        """
        return self._oid

    @property
    def data(self)-> UserDatas:
        """ Get the data of the user.
        Returns:
            The data of the user.
        """
        return self._data
    
    @data.setter
    def data(self, value:UserDatas):
        """ Set the data of the user.

        Args:
            value (UserDatas): The new data of the user.

        Raises:
            TypeError: The data must be a user.
        """
        if not isinstance(value, UserDatas):
            raise TypeError("The data must be a UserDatas.")
        
        old_data = self._data if self._data else "None"
        self._data = value
        self._memorize_changes("data", old_data, value)
    
    @staticmethod
    def generate_unique_oid(
        user_datas:UserDatas = None,
        max_retries:int = 10
        )-> str:
        """
        Generate a unique Object Identifier (OID) for a new UserDatas object.

        This function tries to generate a unique OID by using the 
         UserDatasFunctions.uuid function.
        It checks for uniqueness by looking into the existing `user_datas`
         mapping.

        Args:
            user_datas (UserDatas, optional): The mapping of existing
             user_datas to check for OID uniqueness. 
             Defaults to the singleton instance of the UserDatas class.
            max_retries (int, optional): Maximum number of attempts to generate
             a unique OID. Defaults to 10.

        Returns:
            str: A unique OID.

        Raises:
            ValueError: If a unique OID cannot be generated after `max_retries`
             attempts.
        """
        if user_datas is None:
            # get the singleton instance
            user_datas = PersistentUsers.get_instance()
        for _ in range(max_retries):
            oid = str(UserDatasFunctions.uuid())
            if oid not in user_datas:
                return oid
        raise ValueError(
            f"Failed to generate a unique OID after {max_retries} attempts."
        )

    @property
    def email_send_status_history(self)-> List[EmailEvent]:
        """ Get the email send status history of the user.
        Returns:
            A copy of email send status history of the user.
        """
        return self._email_send_status_history.copy()    
    
    def add_email_send_status(
            self,
            status:EmailSendStatus,
            procedure_name:str
        ):
        """ Add an email send status to the user_datas.
        Args:
            status (EmailSendStatus): The new status of the email
             sent to the applicant.
            procedure_name (str): The name of the procedure used to send the
             email to the applicant.

        Raises:
            TypeError: The status must be an instance of
             EmailSendStatus.
        """
        if not isinstance(status, EmailSendStatus):
            raise TypeError(
                "The status must be an instance of EmailSendStatus."
            )
        old_status = (
            self._email_send_status_history[-1].state 
            if self._email_send_status_history
            else "None"
        )

        # if the status is IN_PREPARATION, generate a new seed
        if status == EmailSendStatus.IN_PREPARATION:
            email_seed = random_string(SEED_LENGTH)
        else:
            email_seed = (
                self._email_send_status_history[-1].seed
                if self._email_send_status_history
                else "None"
            )
        self._email_send_status_history.append(EmailEvent(
            datetime=UserDatasFunctions.now(), 
            state=status,
            function_name=procedure_name,
            seed=email_seed
        ))
        self._memorize_changes("add_email_send_status", old_status, status)
