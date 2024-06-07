# Description: MemberDatas model
# A MemberDatas is an object that represents the member datas manage by the application.
# Creation date: 2024-02-06
# Author: Michaël Launay

from typing import Type, Tuple, List, Any, Optional, Dict, Iterator
from dataclasses import dataclass, fields, make_dataclass
from persistent import Persistent
from persistent.mapping import PersistentMapping
from datetime import datetime
from pyramid.authorization import Allow, ALL_PERMISSIONS
from enum import Enum, unique, IntFlag
from uuid import uuid4
from ZODB.Connection import Connection
import transaction
import random
import string
from datetime import date

# Constants
from alirpunkto.constants_and_globals import (
    _,
    log,
    SEED_LENGTH,
    DEFAULT_COOPERATIVE_BEHAVIOUR_MARK,
)

@unique
class MemberStates(Enum) :
    """States of the member.
    """
    # Created: The member data set is in created mode.
    CREATED = "member_created_value"
    # Draft: The member data set is in draft mode.
    DRAFT = "member_draft_value"
    # Registred: The member data set is in registred mode.
    REGISTRED = "member_registred_value"
    # Data modification requested: The member data set is in modification requested mode.
    DATA_MODIFICATION_REQUESTED = "member_data_modification_request_value"
    # Data modified: The member data set is in modified mode.
    DATA_MODIFIED = "member_datas_modified_value"
    # Exclude: The member data set is in exclude mode.
    EXCLUDED = "member_datas_exclude_value"
    # Deleted: The member data set is in deleted mode.
    DELETED = "member_datas_deleted_value"

    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the member state.
        Args:
            name: The name of the member state.
        Returns:
            The i18n id of the member state.
        """
        match name:

            case cls.CREATED.name :
                return "member_state_created_name"
            case cls.DRAFT.name :
                return "member_state_draft_name"
            case cls.REGISTRED.name :
                return "member_state_registred_name"
            case cls.REGISTRED.value :
                return "member_state_registred_value"
            case cls.DATA_MODIFICATION_REQUESTED.name :
                return "member_data_modification_request_name"
            case cls.DATA_MODIFIED.name :
                return "member_datas_modified_name"
            case cls.CREATED.value :
                return "member_state_created_value"
            case cls.DRAFT.name :
                return "member_state_draft_value"
            case cls.DATA_MODIFICATION_REQUESTED.name :
                return "member_data_modification_request_value"
            case cls.DATA_MODIFIED.name :
                return "member_datas_modified_value"
            case cls.EXCLUDED.name :
                return "member_datas_excluded_name"
            case cls.DELETED.name :
                return "member_datas_deleted_name"
            case cls.EXCLUDED.value :
                return "member_datas_excluded_value"
            case cls.DELETED.value :
                return "member_datas_deleted_value"
            case _ :
                # should never happen
                log.error(f"Unknown member state: {name}")
                return(f"name.lower()")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the member_datas states.
        Returns:
            The names of the member_datas states.
        """
        return MemberStates.__members__.keys()


@unique
class EmailSendStatus(Enum):
    """Status of the email sent to the applicant or member.
    """
    #  In Preparation: The email is being prepared.
    IN_PREPARATION = "email_send_status_in_preparation_value"
    # Sent: The email has been sent.
    SENT = "email_send_status_sent_value"
    # Error: An error occured while sending the email.
    ERROR = "email_send_status_error_value"


@unique
class MemberTypes(Enum) :
    """Types of member.
    """
    # Ordinary: The member is an ordinary member.
    ORDINARY = "member_types_ordinary_value"
    # Cooperator: The member is a cooperator member.
    COOPERATOR = "member_types_cooperator_value"
    @classmethod
    def get_i18n_id(cls, name:Type['MemberTypes']) -> str:
        """Get the i18n id of the member type.
        Args:
            name: The name of the member type.
        Returns:
            The i18n id of the member type.
        """
        match name:
            case cls.ORDINARY.name :
                return "member_types_ordinary"
            case cls.COOPERATOR.name :
                return "member_types_cooperator"
            case cls.ORDINARY.value :
                return "member_types_ordinary_value"
            case cls.COOPERATOR.value :
                return "member_types_cooperator_value"
            case _ :
                # should never happen
                log.error(f"Unknown member type: {name}")
                return(f"name.lower()")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the member types.
        Returns:
            The names of the member types.
        """
        return MemberTypes.__members__.keys()

@unique
class MemberRoles(Enum) :
    """Roles of members.
    """
    # None: No role.
    NONE = "member_role_none_value"
    # Ordinary: The member is an ordinary member.
    ORDINARY = "member_role_ordinary_value"
    # Cooperator: The member is a cooperator member.
    COOPERATOR = "member_role_cooperator_value"
    # Board:  The member is a board member.
    BOARD = "member_role_board_value"
    # MediationArbitrationCouncil: The member is a mediation arbitration
    #  council member.
    MEDIATION_ARBITRATION_COUNCIL = "member_role_mediation_arbitration_council_value"

    @classmethod
    def get_i18n_id(cls, name:Type['MemberRoles']) -> str:
        """Get the i18n id of the member role.
        Args:
            name: The name of the member role.
        Returns:
            The i18n id of the member role.
        """
        match name:
            case cls.NONE.name :
                return "member_roles_none"
            case cls.ORDINARY.name :
                return "member_roles_ordinary"
            case cls.COOPERATOR.name :
                return "member_roles_cooperator"
            case cls.BOARD.name :
                return "member_roles_board"
            case cls.MEDIATION_ARBITRATION_COUNCIL.name :
                return "member_roles_mediation_arbitration_council"
            case cls.ORDINARY.value :
                return "member_roles_ordinary_value"
            case cls.COOPERATOR.value :
                return "member_roles_cooperator_value"
            case cls.BOARD.value :
                return "member_roles_board_value"
            case cls.MEDIATION_ARBITRATION_COUNCIL.value :
                return "member_roles_mediation_arbitration_council_value"
            case _ :
                # should never happen
                log.error(f"Unknown member role: {name}")
                return(f"role_types_{name.lower()}")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the member roles.
        Returns:
            The names of the member roles.
        """
        return MemberRoles.__members__.keys()

@dataclass
class MemberDataEvent:
    """An event.
    """
    datetime:datetime # the datetime of the event
    function_name:str # the name of the function that triggered the event
    value_before:Any # the value of the member_datas before the event
    value_after:Any # the value of the member_datas after the event
    seed:str # the seed of the member_datas at the moment of the event
    def __repr__(self):
        return f"<MemberDataEvent({self.datetime}, "\
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
    @staticmethod
    def get_field_names()-> Iterator[str]:
        """Get the field names of the dataclass.
        Returns:
            An iterator over the field names of the dataclass.
        """
        return (field.name for field in fields(MemberDataEvent))

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
    @staticmethod
    def get_field_names()-> Iterator[str]:
        """Get the field names of the dataclass.
        Returns:
            An iterator over the field names of the dataclass.
        """
        return (field.name for field in fields(EmailEvent))

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

class MemberDataFunctions:
    """A class to store functions used by the MemberDatas class.
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
        return MemberDataFunctions.func_now()
    @staticmethod
    def uuid() -> str:
        """Get a unique identifier (UUID).
        Returns:
            A unique identifier (UUID).
        """
        return MemberDataFunctions.func_uuid()

@dataclass
class MemberDatas:
    fullname: str = None
    fullsurname: str = None
    description: str = None
    nationality: str = None
    birthdate: date = None
    password: str = None
    password_confirm: str = None
    lang1: str = None
    lang2: str = None
    lang3: str = None
    is_active: bool = True
    cooperative_behaviour_mark: float = DEFAULT_COOPERATIVE_BEHAVIOUR_MARK
    cooperative_behaviour_mark_update: date = None
    number_shares_owned: int = 0
    date_end_validity_yearly_contribution: date = None
    unique_member_of: str = ""
    iban: str = None
    date_erasure_all_data: date = None
    role: MemberRoles = MemberRoles.NONE

    def iter_attributes(self)-> Iterator[Tuple[str, Any]]:
        """Iterate over the attributes of the dataclass.
        Returns:
            Iterator[Tuple[str, Any]]: An iterator over the attributes of the
                dataclass.
        """
        for field in fields(self):
            yield field.name, getattr(self, field.name)

    @staticmethod
    def get_field_names()-> Iterator[str]:
        """Get the field names of the dataclass.
        Returns:
            An iterator over the field names of the dataclass.
        """
        return (field.name for field in fields(MemberDatas))

class Members(PersistentMapping):
    """A mapping to store MemberDatas in the ZODB.
    Coulb be used as a singleton if all calls are made through get_instance.
    """
    _instance = None

    @staticmethod
    def get_instance(connection:Connection = None) -> Type['Members']:
        """Get the singleton instance. Not thread safe !
        Args:
            connection: The ZODB connection, could be change for testing.
        Returns:
            The singleton instance.
            This singleton instance is a mapping to store lists of MemberDatas
            subtypes associated with one unique oid.
        Raises:
            TypeError: The connection argument must be an instance of
                    ZODB.Connection.Connection
        """
        if Members._instance is not None:
            #check if the zodb connexion is still alive then return the instance
            try:
                'test' in Members._instance
            except Exception as e:
                log.error(f"Error while getting members instance: {e}")
                raise e
            return Members._instance

        # Check if a ZODB is provided
        if not isinstance(connection, Connection):
            raise TypeError(
                "The connection argument must be an instance of "
                "ZODB.Connection.Connection"
            )

        # check if root exists
        root = connection.root()
        if 'members' not in root:
            connection.root()['members'] = Members()
            transaction.commit()
        Members._instance = connection.root()['members']
        return root['members']

    def __init__(self):
        """Constructor.
        """
        super().__init__()
        self._monitored_members = PersistentMapping()

    @property
    def monitored_members(self)-> PersistentMapping:
        """ Get the monitored members.
        A monitored member is a member that is not in DRAFT or
          APPROUVED or REFUSED state and needs to be monitored.
        For exemple, It could be necessary to send them a reminder email
          to the verifiers if the expiration date is approaching.
        Returns:
            The monitored members.DELETED
        """
        return self._monitored_members

    @property
    def members_emails(self)-> List[str]:
        """Retrieve the emails of all members.

        This method returns a list of email addresses from all members.
        In future versions, this functionality might be enhanced with caching
        and listeners to maintain updated and accurate values.

        Returns:
            List[str]: A list containing the emails of all members.
        """
        return [member.email for member in self.values()]

class Member(Persistent):
    """
    Represents a persistent storage object for member data within the ZODB.

    This class is designed to manage member data, track modifications, and
    handle state transitions securely. It supports recording various member-related
    data, including personal information, state, type, and modification history.
    It's particularly suitable for applications that require detailed audit trails
    and historical data tracking.

    Properties:
        data (MemberDatas): Accesses the data for the member. Supports get and set operations.
        oid (str): Retrieves the unique object identifier. Read-only.
        member_state (MemberStates): Controls the current state of the member. Supports get and set operations.
        type (MemberTypes or None): Defines the type of the member. Supports get and set operations.
        email (str or None): Manages the email address associated with the member. Supports get and set operations.
        seed (str): Retrieves the random string used to generate the OID. Read-only.
        email_send_status_history (list of EmailEvent): Accesses the list that records the email send status history. Supports get and set operations.
        pseudonym (str): Accesses the pseudonym of the member. Supports get and set operations.
        modifications (list of MemberDataEvent): Tracks modifications to the member data. Supports get and set operations.
    """
    __acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]

    def __init__(self,
        data: Optional[MemberDatas] = None,
        oid: Optional[str] = None,
        member_state: MemberStates = MemberStates.DRAFT,
        type: Optional[MemberTypes] = None,
        email: Optional[str] = None,
        seed: Optional[str] = None,
        email_send_status_history: Optional[List[EmailEvent]] = None,
        pseudonym: Optional[str] = None,
        modifications: Optional[List[MemberDataEvent]] = None
        ):
        """
        Initialize a new MemberDatas object.

        Args:
            data (MemberDatas, optional): Initial data for the member. Defaults to None.
            oid (str, optional): A unique object identifier. If not provided, a unique OID is generated. Defaults to None.
            member_state (MemberStates, optional): The current state of the member. Defaults to MemberStates.DRAFT.
            type (MemberTypes or None, optional): The type of the member (e.g., administrator, regular member). Defaults to None.
            email (str or None, optional): The email address associated with the member. Defaults to None.
            seed (str, optional): A random string used to generate the OID. Defaults to None.
            email_send_status_history (list of EmailEvent, optional): A list to record the email send status history. Defaults to an empty list.
            pseudonym (str, optional): The pseudonym of the member. Defaults to None.
            modifications (list of MemberDataEvent, optional): A list to record modifications, where each entry is a dataclass containing the datetime, function name, previous value, new value, and seed. Defaults to an empty list.

        Raises:
            RuntimeError: Raised if an instance already exists with the same OID.

        """
        self._data = data
        # get a unique object id if not provided
        self._oid = oid if oid else Member.generate_unique_oid()
        self._member_state = member_state
        self._type = type
        self._email = email
        self._seed = seed
        self._email_send_status_history = (email_send_status_history
            if email_send_status_history else [])
        self._pseudonym = pseudonym
        self._modifications = modifications if modifications else []
        # get a random seed and record the creation
        self._memorize_changes("__init__", None, self._member_state)

    def _memorize_changes(
        self,
        function_name: Optional[str] = None,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None
        ) -> None:
        """Memorize changes to the member_datas and generate a new seed.

        Args:
            function_name (Optional[str]        # get a random seed and record the creation
): The name of the function that
             triggered the change. Defaults to "_change_seed".
            previous_value (Optional[Any]): The previous value of the
             member_datas property. Defaults to None.
            new_value (Optional[Any]): The new value of the member_datas
            property. Defaults to None.
        """
        # Fallback to "_change_seed" if function_name is None
        function_name = function_name or "_change_seed"
        # Fallback to "None" if self._seed is None
        old_seed = self._seed or "None"

        self._seed = random_string(SEED_LENGTH)

        event = MemberDataEvent(
            datetime=MemberDataFunctions.now(),
            function_name=function_name,
            value_before=previous_value,
            value_after=new_value,
            seed=self._seed
        )

        self._modifications.append(event)
        self._p_changed = True  # Mark the object as changed

    @property
    def seed(self)-> str:
        """ Get the seed of the member.
        Returns:
            The seed of the member.
        """
        return self._seed

    @property
    def member_state(self)-> MemberStates:
        """ Get the state of the member.
        Returns:
            The state of the member.
        """
        return self._member_state

    @member_state.setter
    def member_state(self, value:MemberStates):
        """ Set the state of the member.

        Args:
            value (MemberStates): The new state of the member.

        Raises:
            TypeError: The state must be an instance of MemberStates.
        """
        if not isinstance(value, MemberStates):
            raise TypeError(
                "The state must be an instance of MemberStates."
            )

        old_state = self._member_state.name if self._member_state else "None"
        self._member_state = value
        self._memorize_changes("member_state", old_state, value.name)

    @property
    def type(self)-> MemberTypes:
        """ Get the type of the member.
        Returns:
            The type of the member.
        """
        return self._type

    @type.setter
    def type(self, value:MemberTypes):
        """ Set the type of the member.

        Args:
            value (MemberTypes): The new type of the member.

        Raises:
            TypeError: The type must be an instance of MemberTypes.
        """
        if not isinstance(value, MemberTypes):
            raise TypeError(
                "The type must be an instance of MemberTypes."
            )

        old_type = self._type.name if self._type else "None"
        self._type = value
        self._memorize_changes("type", old_type, value.name)

    @property
    def email(self)-> str:
        """ Get the email of the member.
        Returns:
            The email of the member.
        """
        return self._email

    @email.setter
    def email(self, value:str):
        """ Set the email of the member.

        Args:
            value (str): The new email of the member.

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
        """ Get the pseudonym of the member.
        Returns:
            The pseudonym of the member.
        """
        return self._pseudonym

    @pseudonym.setter
    def pseudonym(self, value:str):
        """ Set the pseudonym of the member.

        Args:
            value (str): The new pseudonym of the member.

        Raises:
            TypeError: The pseudonym must be a string.
        """
        if not isinstance(value, str):
            raise TypeError("The pseudonym must be a string.")

        old_pseudonym = self._pseudonym if self._pseudonym else "None"
        self._pseudonym = value
        self._memorize_changes("pseudonym", old_pseudonym, value)

    @property
    def modifications(self)-> List[MemberDataEvent]:
        """ Get the modifications of the member.
        Returns:
            A copy of modifications of the member_datas as a list of
            member.
        """
        return self._modifications.copy()

    @property
    def oid(self)-> str:
        """ Get the oid of the member.
        Returns:
            The oid of the member.
        """
        return self._oid

    @property
    def data(self)-> MemberDatas:
        """ Get the data of the member.
        Returns:
            The data of the member.
        """
        return self._data

    @data.setter
    def data(self, value:MemberDatas):
        """ Set the data of the member.

        Args:
            value (MemberDatas): The new data of the member.

        Raises:
            TypeError: The data must be a member.
        """
        if not isinstance(value, MemberDatas):
            raise TypeError("The data must be a MemberDatas.")

        old_data = self._data if self._data else "None"
        self._data = value
        self._memorize_changes("data", old_data, value)

    @staticmethod
    def generate_unique_oid(
        member_datas:MemberDatas = None,
        max_retries:int = 10
        )-> str:
        """
        Generate a unique Object Identifier (OID) for a new MemberDatas object.

        This function tries to generate a unique OID by using the
         MemberDataFunctions.uuid function.
        It checks for uniqueness by looking into the existing `member_datas`
         mapping.

        Args:
            member_datas (MemberDatas, optional): The mapping of existing
             member_datas to check for OID uniqueness.
             Defaults to the singleton instance of the MemberDatas class.
            max_retries (int, optional): Maximum number of attempts to generate
             a unique OID. Defaults to 10.

        Returns:
            str: A unique OID.

        Raises:
            ValueError: If a unique OID cannot be generated after `max_retries`
             attempts.
        """
        if member_datas is None:
            # get the singleton instance
            member_datas = Members.get_instance()
        for _ in range(max_retries):
            oid = str(MemberDataFunctions.uuid())
            if oid not in member_datas:
                return oid
        raise ValueError(
            f"Failed to generate a unique OID after {max_retries} attempts."
        )

    @property
    def email_send_status_history(self)-> List[EmailEvent]:
        """ Get the email send status history of the member.
        Returns:
            A copy of email send status history of the member.
        """
        return self._email_send_status_history.copy()

    def generate_seed(self)-> str:
        """ Generate a seed for the member.
        Returns:
            A seed for the member.
        """
        return random_string(SEED_LENGTH)

    def add_email_send_status(
            self,
            status:EmailSendStatus,
            procedure_name:str
        ):
        """ Add an email send status to the member_datas.
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
            email_seed = self.generate_seed()
        else:
            email_seed = (
                self._email_send_status_history[-1].seed
                if self._email_send_status_history
                else "None"
            )
        self._email_send_status_history.append(EmailEvent(
            datetime=MemberDataFunctions.now(),
            state=status,
            function_name=procedure_name,
            seed=email_seed
        ))
        self._memorize_changes("add_email_send_status", old_status, status)
    @staticmethod
    def get_field_names()-> Iterator[str]:
        """Get the field names of the dataclass.
        Returns:
            An iterator over the field names of the dataclass.
        >>> list(Member.get_field_names())
        ['data', 'email', 'email_send_status_history', 'member_state', 'modifications', 'oid', 'pseudonym', 'seed', 'type']
        """
        field_names = [name for name in dir(Member)
            if isinstance(getattr(Member, name), property)
        ]
        return iter(field_names)