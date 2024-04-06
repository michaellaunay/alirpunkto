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

# Constants
from alirpunkto.constants_and_globals import (
    _,
    log,
    SEED_LENGTH,
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
class Permissions(IntFlag):
    """Access permissions to attributes for any member.
    This class represents the permissions for member attributes.
    Each permission is represented as a bit flag, allowing for easy combination
    of multiple permissions.

    Attributes:
        NONE: No access permission.
        ACCESS: The field is accessible but the value is not shown like a
            password.
        READ: Read permission.
        WRITE: Write permission.
        EXECUTE: Execute permission.
        CREATE: Create permission.
        DELETE: Delete permission.
        TRAVERSE: Traverse permission.
        RENAME: Rename permission.
        DELETE_CHILD: Delete child permission.
        ADMIN: Admin permission.
    """
    # None: No permission
    NONE =         0b00000000000000000000
    # Access: The field is accessible but the value is not shown like password
    ACCESS =       0B00000000000000000001
    # Read: Read permission
    READ =         0B00000000000000000010
    # Write: Write permission
    WRITE =        0B00000000000000000100
    # Execute: Execute permission
    EXECUTE =      0B00000000000000001000
    # Create: Create permission
    CREATE =       0B00000000000000010000
    # Delete: Delete permission
    DELETE =       0B00000000000000100000
    # Traverse: Traverse permission
    TRAVERSE =     0B00000000000001000000
    # Rename: Rename permission
    RENAME =       0B00000000000010000000
    # Delete_child: Delete child permission
    DELETE_CHILD = 0B00000000000100000000
    # Admin: Admin permission
    ADMIN =        0B00000000001000000000

    @classmethod
    def get_i18n_id(cls, name:Type['Permissions']) -> str:
        """Get the i18n id of the permission.
        Args:
            name: The name of the permission.
            get_value: If True, return the name of the permission, else return the name.
        Returns:
            The i18n id of the permission.
        """
        match name:
            case cls.NONE.name :
                return "access_permissions_none"
            case cls.NONE.value :
                return "access_permissions_none_value"
            case cls.ACCESS.name:
                return "access_permissions_access"
            case cls.ACCESS.value:
                return "access_permissions_access_value"
            case cls.READ.name :
                return "access_permissions_read"
            case cls.READ.value :
                return "access_permissions_read_value"
            case cls.WRITE.name :
                return "access_permissions_write"
            case cls.WRITE.value :
                return "access_permissions_write_value"
            case cls.EXECUTE.name :
                return "access_permissions_execute"
            case cls.EXECUTE.value :
                return "access_permissions_execute_value"
            case cls.CREATE.name :
                return "access_permissions_create"
            case cls.CREATE.value :
                return "access_permissions_create_value"
            case cls.DELETE.name :
                return "access_permissions_delete"
            case cls.DELETE.value :
                return "access_permissions_delete_value"
            case cls.TRAVERSE.name :
                return "access_permissions_traverse"
            case cls.TRAVERSE.value :
                return "access_permissions_traverse_value"
            case cls.RENAME.name :
                return "access_permissions_rename"
            case cls.RENAME.value :
                return "access_permissions_rename_value"
            case cls.DELETE_CHILD.name :
                return "access_permissions_delete_child"
            case cls.DELETE_CHILD.value :
                return "access_permissions_delete_child_value"
            case cls.ADMIN.name :
                return "access_permissions_admin"
            case cls.ADMIN.value :
                return "access_permissions_admin_value"
            case _ :
                # should never happen
                log.error(f"Unknown access permission: {name}")
                return(f"name.lower()")
    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the access permissions.
        Returns:
            The names of the access permissions.
        """
        return Permissions.__members__.keys()
    @staticmethod
    def get_permissions(permission:int) \
        -> Iterator[Type['Permissions']]:
        """Get the permissions from int.
        Returns:
            The access permissions as a list.
        """
        return (perm
            for perm in Permissions.__members__.values()
            if permission & perm.value
        )

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
class MemberDatasEvent:
    """An event.
    """
    datetime:datetime # the datetime of the event
    function_name:str # the name of the function that triggered the event
    value_before:Any # the value of the member_datas before the event
    value_after:Any # the value of the member_datas after the event
    seed:str # the seed of the member_datas at the moment of the event
    def __repr__(self):
        return f"<MemberDatasEvent({self.datetime}, "\
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
        return (field.name for field in fields(MemberDatasEvent))

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

class MemberDatasFunctions:
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
        return MemberDatasFunctions.func_now()
    @staticmethod
    def uuid() -> str:
        """Get a unique identifier (UUID).
        Returns:
            A unique identifier (UUID).
        """
        return MemberDatasFunctions.func_uuid()
    
@dataclass
class MemberDatas:
    fullname: str = None
    fullsurname: str = None
    description: str = None
    nationality: str = None
    birthdate: str = None
    password: str = None
    password_confirm: str = None
    lang1: str = None
    lang2: str = None
    lang3: str = None
    cooperative_behaviour_mark: int = 0
    cooperative_behaviour_mark_updated: str = None
    number_shares_owned: int = 0
    date_end_validity_yearly_contribution: str = None
    iban: str = None
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

# MemberDataPermissions is a dataclass that stores the permissions for each
# attribute of the MemberDatas dataclass.
MemberDataPermissions = make_dataclass(
    "MemberDataPermissions",
    [(name, Permissions, Permissions.NONE)
        for name in MemberDatas.get_field_names()]
)
MemberDataPermissionsType = Type[MemberDataPermissions]

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
        voters (list): Manages the list of voters associated with the member. Supports get and set operations.
        member_state (MemberStates): Controls the current state of the member. Supports get and set operations.
        type (MemberTypes or None): Defines the type of the member. Supports get and set operations.
        email (str or None): Manages the email address associated with the member. Supports get and set operations.
        votes (dict): Accesses the dictionary of votes associated with the member. Supports get and set operations.
        seed (str): Retrieves the random string used to generate the OID. Read-only.
        email_send_status_history (list of EmailEvent): Accesses the list that records the email send status history. Supports get and set operations.
        challenge (tuple[str, int]): Manages the math challenge and its solution. Supports get and set operations.
        pseudonym (str): Accesses the pseudonym of the member. Supports get and set operations.
        modifications (list of MemberDatasEvent): Tracks modifications to the member data. Supports get and set operations.
    """
    __acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]

    def __init__(self,
        data: Optional[MemberDatas] = None,
        oid: Optional[str] = None,
        voters: Optional[List[str]] = None,
        member_state: MemberStates = MemberStates.DRAFT,
        type: Optional[MemberTypes] = None,
        email: Optional[str] = None,
        votes: Optional[Dict[str, int]] = None,
        seed: Optional[str] = None,
        email_send_status_history: Optional[List[EmailEvent]] = None,
        challenge: Optional[Tuple[str, int]] = None,
        pseudonym: Optional[str] = None,
        modifications: Optional[List[MemberDatasEvent]] = None
        ):
        """
        Initialize a new MemberDatas object.

        Args:
            data (MemberDatas, optional): Initial data for the member. Defaults to None.
            oid (str, optional): A unique object identifier. If not provided, a unique OID is generated. Defaults to None.
            voters (list, optional): A list of voters associated with the member. Defaults to an empty list.
            member_state (MemberStates, optional): The current state of the member. Defaults to MemberStates.DRAFT.
            type (MemberTypes or None, optional): The type of the member (e.g., administrator, regular member). Defaults to None.
            email (str or None, optional): The email address associated with the member. Defaults to None.
            votes (dict, optional): A dictionary of votes associated with the member. Defaults to an empty dict.
            seed (str, optional): A random string used to generate the OID. Defaults to None.
            email_send_status_history (list of EmailEvent, optional): A list to record the email send status history. Defaults to an empty list.
            challenge (tuple[str, int], optional): A tuple containing a string math challenge and its solution as an integer. Defaults to None.
            pseudonym (str, optional): The pseudonym of the member. Defaults to None.
            modifications (list of MemberDatasEvent, optional): A list to record modifications, where each entry is a dataclass containing the datetime, function name, previous value, new value, and seed. Defaults to an empty list.

        Raises:
            RuntimeError: Raised if an instance already exists with the same OID.

        """
        self._data = data
        # get a unique object id if not provided
        self._oid = oid if oid else Member.generate_unique_oid()
        self._voters = voters if voters else []
        self._member_state = member_state
        self._type = type
        self._email = email
        self._votes = votes if votes else {}
        self._seed = seed
        self._email_send_status_history = (email_send_status_history
            if email_send_status_history else [])
        self._challenge = challenge
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

        event = MemberDatasEvent(
            datetime=MemberDatasFunctions.now(), 
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
    def modifications(self)-> List[MemberDatasEvent]:
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
         MemberDatasFunctions.uuid function.
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
            oid = str(MemberDatasFunctions.uuid())
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
            datetime=MemberDatasFunctions.now(), 
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

# MemberPermissions is a dataclass that stores the permissions for each
# attribute of the Member dataclass.
MemberPermissions = make_dataclass(
    "MemberPermissions", [
        ((name, Permissions, Permissions.NONE) if name != 'data'
            else (name, MemberDataPermissions, MemberDataPermissions())
        ) for name in Member.get_field_names()
    ]
)
MemberPermissionsType = Type[MemberPermissions]

# Create a mapping to store the permissions for each member state.
# The mapping is structured as follows:
# - The key is the member state.
# - The value is a MemberPermissions dataclass that stores
#   the permissions for each attribute of the Member dataclass.
access = {
    'Owner' : {
        MemberStates.CREATED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.NONE,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DRAFT:{
            MemberPermissions(
                    data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    fullsurname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    description=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    nationality=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    birthdate=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    password=Permissions.ACCESS | Permissions.WRITE,
                    password_confirm=Permissions.ACCESS | Permissions.WRITE,
                    lang1=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang2=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang3=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.ACCESS | Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.REGISTRED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.READ,
                    cooperative_behaviour_mark_updated=Permissions.READ,
                    number_shares_owned=Permissions.READ,
                    date_end_validity_yearly_contribution=Permissions.READ,
                    iban=Permissions.READ,
                    role=Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DATA_MODIFICATION_REQUESTED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    nationality=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE | Permissions.WRITE,
                    password_confirm=Permissions.NONE | Permissions.WRITE,
                    lang1=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang2=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang3=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark_updated=Permissions.ACCESS | Permissions.READ,
                    number_shares_owned=Permissions.ACCESS | Permissions.READ,
                    date_end_validity_yearly_contribution=Permissions.ACCESS | Permissions.READ,
                    iban=Permissions.READ | Permissions.WRITE,
                    role=Permissions.ACCESS | Permissions.READ,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DATA_MODIFIED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.EXCLUDED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
        MemberStates.DELETED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ,
                    fullsurname=Permissions.ACCESS | Permissions.READ,
                    description=Permissions.ACCESS | Permissions.READ,
                    nationality=Permissions.ACCESS | Permissions.READ,
                    birthdate=Permissions.ACCESS | Permissions.READ,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.ACCESS | Permissions.READ,
                    lang2=Permissions.ACCESS | Permissions.READ,
                    lang3=Permissions.ACCESS | Permissions.READ,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.ACCESS | Permissions.READ,
                email=Permissions.ACCESS | Permissions.READ,
                votes=Permissions.NONE,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        }        
    },
    'Admin' : {
        MemberStates.CREATED:{
            MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    fullsurname=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    description=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    nationality=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    birthdate=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    password=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    password_confirm=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang1=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang2=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    lang3=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    cooperative_behaviour_mark_updated=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    number_shares_owned=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    date_end_validity_yearly_contribution=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    iban=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                    role=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                type=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                email=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                votes=Permissions.ACCESS | Permissions.READ,
                seed=Permissions.ACCESS,
                email_send_status_history=Permissions.ACCESS | Permissions.READ,
                challenge=Permissions.ACCESS | Permissions.READ,
                pseudonym=Permissions.ACCESS | Permissions.READ | Permissions.WRITE,
                modifications=Permissions.ACCESS | Permissions.READ
            )
        },
    },
    'Ordinary' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'Cooperator' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'Board' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'MediationArbitrationCouncil' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'CandidatesMissingShareYearContrib' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'CandidatesMissingShare' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'CandidatesMissingYearContrib' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'Sanctioned' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    },
    'SanctionedMissingYearContrib' : {
        MemberStates.CREATED:{
             MemberPermissions(
                data=MemberDataPermissions(
                    fullname=Permissions.NONE,
                    fullsurname=Permissions.NONE,
                    description=Permissions.NONE,
                    nationality=Permissions.NONE,
                    birthdate=Permissions.NONE,
                    password=Permissions.NONE,
                    password_confirm=Permissions.NONE,
                    lang1=Permissions.NONE,
                    lang2=Permissions.NONE,
                    lang3=Permissions.NONE,
                    cooperative_behaviour_mark=Permissions.NONE,
                    cooperative_behaviour_mark_updated=Permissions.NONE,
                    number_shares_owned=Permissions.NONE,
                    date_end_validity_yearly_contribution=Permissions.NONE,
                    iban=Permissions.NONE,
                    role=Permissions.NONE
                ),
                oid=Permissions.ACCESS | Permissions.READ,
                member_state=Permissions.ACCESS | Permissions.READ,
                type=Permissions.NONE,
                email=Permissions.NONE,
                votes=Permissions.NONE,
                seed=Permissions.NONE,
                email_send_status_history=Permissions.NONE,
                challenge=Permissions.NONE,
                pseudonym=Permissions.ACCESS | Permissions.READ,
                modifications=Permissions.NONE
            )    
        }
    }
}


def get_member_data_access_permissions(acceded: Member, accessor : Member) -> MemberPermissionsType:
    """Get the data access permissions for a member accessing another member's data.
    Args:
        acceded (Member): The member whose data is being accessed.
        accessor (Member): The member accessing the data.
    Returns:
        MemberPermissions: The data access permissions for the accessor.
    """
    permissions = []
    is_owner = acceded == accessor
    # Check if the accessor is the same as the acceded member
    if is_owner:
        return access['Owner'][acceded.member_state]        
    else:
        return access[accessor.type.name][acceded.member_state]

"""_summary_
Explanation of permissions by roles and states of Members and Applications

## Anonymous

The anonymous user can only see what is made public.
They can view the registration procedure.

## States in alirpunkto

### Here are the states of Members in alirpunkto, these states are used to manage the modification of member data.

- CREATED
- DRAFT
- REGISTRED
- DATA_MODIFICATION_REQUESTED
- DATA_MODIFIED
- EXCLUDED
- DELETED

### Here are the states of Applications (states that are added to the previous ones)

- DRAFT
- EMAIL_VALIDATION
- CONFIRMED_HUMAN
- UNIQUE_DATA
- PENDING
- APPROVED
- REFUSED

### Here are the groups a Member can belong to

- ordinaryMembersGroup
- cooperatorsGroup
- boardMembersGroup
- mediationArbitrationCouncilGroup
- candidatesMissingShareYearContribGroup
- candidatesMissingShareGroup
- candidatesMissingYearContribGroup
- sanctionedGroup
- sanctionedMissingYearContribGroup

## List of variables

- First names (as they appear in official identity documents)
- Last names (as they appear in official identity documents)
- Date of birth
- Nationality (from the Member States of the European Union)
- Display name
- Password
- Confirm password
- Cooperator number
- Cooperative Behavior Note
- Date and time of last update of the Cooperative Behavior Note
- Email address
- Rank 1 interaction language
- Rank 2 interaction language (@TODO Add the option "not specified" in the form)
- Rank 3 interaction language (@TODO Add the option "not specified" in the form)
- User profile text
- User profile picture / avatar
- Role in the Cooperative: * None, * Ordinary Member of the Community, * Cooperator, * Member of the Board, * Member of the Mediation and Arbitration Council
- uniqueMemberOf
- Number of shares held
- End date of current annual contribution validity
- Date when data of resigning or excluded user must be erased

- Bank account IBAN number

## Draft Ordinary Candidate

The state of the Application in AlirPunkto is EMAIL_VALIDATION.
The Member part of the Application is in the DRAFT state.
The Member type in AlirPunkto is ORDINARY.
The Ordinary Candidate must validate their email address.
They can only enter their email and cannot see any other fields.

### List of visible or editable variables

- First names: invisible - not editable
- Last names: invisible - not editable
- Date of birth: invisible - not editable
- Nationality: invisible - not editable
- Username: invisible - not editable
- Password: invisible - not editable
- Confirm password: invisible - not editable
- Cooperator number: invisible - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - EDITABLE - REQUIRED
- Rank 1 interaction language: invisible - not editable
- Rank 2 interaction language: invisible - not editable
- Rank 3 interaction language: invisible - not editable
- User profile text: invisible - not editable
- User profile picture / avatar: invisible - not editable
- Role in the Cooperative: invisible - not editable
- uniqueMemberOf: invisible - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable
Once the email is entered, alirpunkto sends the Challenge email.
The list of possible states is as follows:

## Human Ordinary Candidate

The state of the Application in AlirPunkto is CONFIRMED_HUMAN.
The Member part of the Application is in the DRAFT state.
The Human Ordinary Candidate is an Ordinary Candidate who has validated their address and human
character by answering the mathematical challenge, but has not yet entered their data.

### List of visible or editable variables

- First names: invisible - not editable
- Last names: invisible - not editable
- Date of birth: invisible - not editable
- Nationality: invisible - not editable
- Username: VISIBLE - EDITABLE - REQUIRED (Leading and trailing spaces are removed)
- Password: VISIBLE - EDITABLE - REQUIRED
- Confirm password: VISIBLE - EDITABLE - REQUIRED
- Cooperator number: VISIBLE - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - not editable
- Rank 1 interaction language: VISIBLE - EDITABLE - REQUIRED
- Rank 2 interaction language: VISIBLE - EDITABLE - optional
- Rank 3 interaction language: VISIBLE - EDITABLE - optional
- User profile text: invisible - not editable
- User profile picture / avatar: invisible - not editable
- Role in the Cooperative: invisible - not editable
- uniqueMemberOf: invisible - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable

## Ordinary Member

The state of the Application in AlirPunkto is APPROVED.
The member is part of the "ordinaryMembersGroup".
The Application part is cleared of its data once written to LDAP.
The Member part of the Application is in the REGISTRED state.
The Ordinary Member is a "Human Ordinary Candidate" who has registered their personal data.
They become an ordinary member of the community.
They can submit a request to become a cooperator, at most once every 30 days (configurable duration).
They can resign and they can be excluded.

Upon each login, alirpunkto offers them to modify or complete their data according to the following list.

### List of visible or editable variables

- First names: invisible - not editable
- Last names: invisible - not editable
- Date of birth: invisible - not editable
- Nationality: invisible - not editable
- Username: VISIBLE - not editable
- Password: invisible - not editable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not editable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - EDITABLE - optional
- Rank 1 interaction language: VISIBLE - EDITABLE - optional
- Rank 2 interaction language: VISIBLE - EDITABLE - optional
- Rank 3 interaction language: VISIBLE - EDITABLE - optional
- User profile text: VISIBLE - EDITABLE - optional
- User profile picture / avatar: VISIBLE - EDITABLE - optional
- Role in the Cooperative: VISIBLE - not editable
- uniqueMemberOf: VISIBLE - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable

## Deletion of Ordinary Member

Whether they have resigned or have been excluded by the administrator (without any particular guarantee,
as the Ordinary Member of the Community does not benefit from the protection provided by the Cooperative's bylaws to the Cooperators), alirpunkto deletes the account data of the Ordinary Member, but keeps the pseudonym, deletion date, and reason for deletion (resignation or exclusion). If they have resigned, their Member status is DELETED, if they have been excluded, their Member status is EXCLUDED.

## Draft Cooperative Candidate

The state of the Member part of the Application in AlirPunkto is DRAFT.
The state of the Application part in AlirPunkto is DRAFT.
Alirpunkto requests the email.

### List of visible or editable variables

(same as the Draft Ordinary Candidate)
The candidate submits their email.
Alirpunkto sends the challenge email.
The state of the Application in AlirPunkto is EMAIL_VALIDATION.

## Human Cooperative Candidate

The state of the Member part of the Application in AlirPunkto is DRAFT.
The user has answered the mathematical challenge and thus proved that they are human. The state of the Application part in AlirPunkto is CONFIRMED_HUMAN.

### List of visible or editable variables

- First names: VISIBLE - EDITABLE - REQUIRED
- Last names: VISIBLE - EDITABLE - REQUIRED
- Date of birth: VISIBLE - EDITABLE - REQUIRED
- Nationality: VISIBLE - EDITABLE - REQUIRED
- Username: VISIBLE - EDITABLE - REQUIRED (Leading and trailing spaces are removed)
- Password: VISIBLE - EDITABLE - REQUIRED
- Confirm password: VISIBLE - EDITABLE - REQUIRED
- Cooperator number: VISIBLE - not editable
- Cooperative Behavior Note: invisible - not editable
- Date and time of last update of the Cooperative Behavior Note: invisible - not editable
- Email address: VISIBLE - not editable
- Rank 1 interaction language: VISIBLE - EDITABLE - REQUIRED
- Rank 2 interaction language: VISIBLE - EDITABLE - optional
- Rank 3 interaction language: VISIBLE - EDITABLE - optional
- User profile text: invisible - not editable
- User profile picture / avatar: invisible - not editable
- Role in the Cooperative: invisible - not editable
- uniqueMemberOf: invisible - not editable
- Number of shares held: invisible - not editable
- End date of current annual contribution validity: invisible - not editable
- Date when data of resigning or excluded user must be erased: invisible - not editable
- Bank account IBAN number: invisible - not editable

## Human Cooperative Candidate awaiting verification

The state of the Member part of the Application in AlirPunkto is DRAFT.
The uniqueness of identity data (last name(s), first name(s), date of birth) has been verified in the list of existing Cooperators (cooperatorsGroup, candidatesMissingShareGroup, candidatesMissingYearContribGroup, candidatesMissingShareYearContribGroup, sanctionedGroup, sanctionedMissingYearContribGroup) and in former Cooperators (resigned or excluded) whose identity data is still in the database because they have not been reimbursed and the Quarantine period has not yet passed, so the Application part in AlirPunkto is in the UNIQUE_DATA state.
If the candidate does not declare having sent the verification email, alirpunkto does nothing until a verifier logs in with the voting URL. Alirpunkto can remind the candidate.
If the candidate indicates having sent the verification email, then alirpunkto notifies the verifiers in turn.
The state of the Application is then PENDING.

### List of visible or modifiable variables

- First names: VISIBLE - not modifiable
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable
- Username: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: invisible - not modifiable
- Date and time of last update of the Cooperative Behavior Note: invisible - not modifiable
- Email address: VISIBLE - MODIFIABLE - optional
- Rank 1 interaction language: VISIBLE - MODIFIABLE - optional
- Rank 2 interaction language: VISIBLE - MODIFIABLE - optional
- Rank 3 interaction language: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - MODIFIABLE - optional
- User profile picture / avatar: VISIBLE - MODIFIABLE - optional
- Role in the Cooperative: invisible - not modifiable
- uniqueMemberOf: invisible - not modifiable
- Number of shares held: invisible - not modifiable
- End date of current annual contribution validity: invisible - not modifiable
- Date when data of resigning or excluded user must be erased: invisible - not modifiable
- Bank account IBAN number: invisible - not modifiable

## Rejected human cooperative candidate

If the Verifiers have not validated the candidate's identity data, the member becomes an Ordinary Member of the Community with full rights (see above).
They are informed that the validation procedure for their identity data has failed, and that they are therefore only an Ordinary Member of the Community.
Their identity data (first name(s), last name(s), date of birth) is deleted.

## Candidate without share and without up-to-date annual contribution

The candidate's identity data has been validated by the Verifiers, and therefore the status of the Application in AlirPunkto is APPROVED.

## The member belongs to 2 groups: ordinaryMembersGroup, candidatesMissingShareYearContribGroup.
#### List of visible or modifiable variables

- First names: VISIBLE
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable

- Pseudonym: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: invisible - not modifiable
- Last update date and time of Cooperative Behavior Note: invisible - not modifiable
- Email address: VISIBLE - MODIFIABLE - optional
- Interaction language rank 1: VISIBLE - MODIFIABLE - optional
- Interaction language rank 2: VISIBLE - MODIFIABLE - optional
- Interaction language rank 3: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - MODIFIABLE - optional
- User profile image/avatar: VISIBLE - MODIFIABLE - optional
- Role in the Cooperative: VISIBLE - not modifiable
- uniqueMemberOf: VISIBLE - not modifiable
- Number of owned shares: VISIBLE - not modifiable (modification only through online sale on Drupal)
- End date of current annual contribution validity: VISIBLE - not modifiable (modification only through online sale on Drupal)
- Date when data of resigning or excluded user should be erased: invisible - not modifiable
- IBAN bank account number: VISIBLE - MODIFIABLE - optional

### Resignation of a member

In this case, alirpunkto does not ask for their IBAN, and keeps their personal data during the quarantine period, then retains their pseudonym, the account deletion date, and the reason for their departure (i.e., resignation).

The administrator can exclude them in the same way as excluding an ordinary member of the Community, as the person, not having any shares, is not legally a Cooperator and therefore does not benefit from the protections that the Cooperative's bylaws provide to its members.

## Candidate without shares but with up-to-date annual contribution

The status of the Candidate in AlirPunkto is APPROVED.

The member belongs to the 2 groups: ordinaryMembersGroup, candidatesMissingShareGroup.

### List of visible or modifiable variables

(same as the Candidate without shares and without up-to-date annual contribution)

They can resign and be excluded under the same conditions and for the same reasons as the candidate without shares or up-to-date annual contribution. Their annual contribution is lost.

## Candidate with shares but without up-to-date annual contribution

They belong to the 2 groups: ordinaryMembersGroup, candidatesMissingYearContribGroup.

### List of visible or modifiable variables

- First names: VISIBLE - not modifiable
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable
- Pseudonym: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Last update date and time of Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Email address: VISIBLE - MODIFIABLE - optional
- Interaction language rank 1: VISIBLE - MODIFIABLE - optional
- Interaction language rank 2: VISIBLE - MODIFIABLE - optional
- Interaction language rank 3: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - MODIFIABLE - optional
- User profile image/avatar: VISIBLE - MODIFIABLE - optional
- Role in the Cooperative: VISIBLE - not modifiable
- uniqueMemberOf: VISIBLE - not modifiable
- Number of owned shares: VISIBLE - not modifiable (modification only through online sale on Drupal)
- End date of current annual contribution validity: VISIBLE - not modifiable (modification only through online sale on Drupal)
- Date when data of resigning or excluded user should be erased: invisible - not modifiable
- IBAN bank account number: VISIBLE - MODIFIABLE - optional

They can resign and be excluded under the conditions and procedures described below.

## Cooperator with shares and up-to-date annual contribution

They are considered a cooperative member, belong to the 2 groups: ordinaryMembersGroup, cooperatorsGroup.

### List of visible or modifiable variables

(same as the Candidate with shares but without up-to-date annual contribution)

They can resign and be excluded under the conditions and procedures described below.

## Sanctioned Cooperator

The Cooperator sanctioned by the Mediation and Arbitration Council following a procedure defined by the bylaws (this procedure is outside the scope of AlirPunkto) is in the groups: ordinaryMembersGroup and sanctionedGroup.

### List of visible or modifiable variables

(same as the Candidate with shares but without up-to-date annual contribution)

They can resign and be excluded under the conditions and procedures described below.

### Sanctioned Cooperator without up-to-date annual contribution

The Cooperator sanctioned by the Mediation and Arbitration Council following a procedure defined by the bylaws (this procedure is outside the scope of AlirPunkto) and whose annual contribution is no longer up-to-date, or the Candidate without up-to-date annual contribution sanctioned by the Mediation and Arbitration Council, is in the groups: ordinaryMembersGroup and sanctionedMissingYearContribGroup.

### List of visible or modifiable variables

(same as the Candidate with shares but without up-to-date annual contribution)

They can resign and be excluded under the conditions and procedures described below.

## Resignation of a member from the groups candidatesMissingYearContribGroup, cooperatorsGroup, sanctionedGroup, sanctionedMissingYearContribGroup

If the member resigns, they no longer belong to any group. Alirpunkto asks them to fill in their IBAN.

So, as long as they have not been reimbursed for their share (= as long as the number of shares they own is different from 0), they retain access to AlirPunkto (to fill in their IBAN details) and their identity data is retained.

Every time they log in, aliripunkto reminds them that their IBAN is needed for reimbursement.

Once they have been reimbursed and the Quarantine period has expired, alirpunkto informs them that their data has been deleted and then deletes all data from the account, retaining only their pseudonym, the date, and the reason for their departure (i.e., resignation).

### List of visible or modifiable variables

- First names: VISIBLE - not modifiable
- Last names: VISIBLE - not modifiable
- Date of birth: VISIBLE - not modifiable
- Nationality: VISIBLE - not modifiable
- Pseudonym: VISIBLE - not modifiable
- Password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Confirm password: invisible - not modifiable (modifiable only through the "forgot password" procedure)
- Cooperator number: VISIBLE - not modifiable
- Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Last update date and time of Cooperative Behavior Note: VISIBLE - not modifiable (only through KuneAgi instances)
- Email address: VISIBLE - MODIFIABLE - optional
- Interaction language rank 1: VISIBLE - MODIFIABLE - optional
- Interaction language rank 2: VISIBLE - MODIFIABLE - optional
- Interaction language rank 3: VISIBLE - MODIFIABLE - optional
- User profile text: VISIBLE - not modifiable
- User profile image/avatar: VISIBLE - not modifiable
- Role in the Cooperative: VISIBLE - not modifiable
- uniqueMemberOf: VISIBLE - not modifiable
- Number of owned shares: VISIBLE - not modifiable (modification only through online sale on Drupal)
- End date of current annual contribution validity: VISIBLE - not modifiable (modification only through online sale on Drupal)
- Date when data of resigning or excluded user should be erased: VISIBLE - not modifiable
- IBAN bank account number: VISIBLE - MODIFIABLE - optional

## Exclusion of a member from the groups candidatesMissingYearContribGroup, cooperatorsGroup, sanctionedGroup, sanctionedMissingYearContribGroup

The member can be excluded by the Mediation and Arbitration Council, following the procedure defined in the Cooperative's bylaws (this procedure is outside the scope of AlirPunkto). The procedure to follow in case of exclusion, and the list of visible or modifiable variables, are identical to those in the case of resignation, with the only difference being that the reason for departure is exclusion.
"""