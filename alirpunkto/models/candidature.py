# Description: Candidature model
#   A candidature is an object that represents a candidate's application.
# Creation date: 2023-07-22
# Author: Michaël Launay

from typing import Type, Callable, Tuple, List, Any, Optional
from dataclasses import dataclass
from persistent import Persistent
from persistent.mapping import PersistentMapping
from datetime import datetime
from pyramid.authorization import Allow, ALL_PERMISSIONS
from enum import Enum, unique
from uuid import uuid4
from ZODB.FileStorage import FileStorage
from ZODB.Connection import Connection
from logging import getLogger
import transaction
import random
import string

SEED_LENGTH = 10
log = getLogger('alirpunkto')



@unique
class CandidatureStates(Enum) :
    """States of candidatures.
    """
    DRAFT = "candidature_states_draft_value" # "Draft: The application is in draft mode."
    EMAIL_VALIDATION = "candidature_states_email_validation_value" # "Email Validation: The state where the Applicant's email address is awaiting validation."
    CONFIRMED_HUMAN = "candidature_states_confirmed_human_value" # "ConfirmedHuman: The Applicant's email address is verified, and humanity proof is provided."
    UNIQUE_DATA = "candidature_states_unique_data_value" # "UniqueData: The Applicant has entered their personal identification data."
    PENDING = "candidature_states_pending_value" # "Pending: After the submission of the application and while waiting for verification by the verifiers."
    APPROVED = "candidature_states_approved_value" # "Approved: The application has been accepted."
    REFUSED = "candidature_states_refused_value" # "Refused: The application has been denied."

    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the candidature state.
        Args:
            name: The name of the candidature state.
        Returns:
            The i18n id of the candidature state.
        """
        match name:
            case cls.DRAFT.name :
                return "candidature_states_draft"
            case cls.EMAIL_VALIDATION.name :
                return "candidature_states_email_validation"
            case cls.CONFIRMED_HUMAN.name :
                return "candidature_states_confirmed_human"
            case cls.UNIQUE_DATA.name :
                return "candidature_states_unique_data"
            case cls.PENDING.name :
                return "candidature_states_pending"
            case cls.APPROVED.name :
                return "candidature_states_approved"
            case cls.REFUSED.name :
                return "candidature_states_refused"
            case cls.DRAFT.value :
                return "candidature_states_draft_value"
            case cls.EMAIL_VALIDATION.value :
                return "candidature_states_email_validation_value"
            case cls.CONFIRMED_HUMAN.value :
                return "candidature_states_confirmed_human_value"
            case cls.UNIQUE_DATA.value :
                return "candidature_states_unique_data_value"
            case cls.PENDING.value :
                return "candidature_states_pending_value"
            case cls.APPROVED.value :
                return "candidature_states_approved_value"
            case cls.REFUSED.value :
                return "candidature_states_refused_value"
            case _ :
                # should never happen
                log.error(f"Unknown candidature state: {name}")
                return(f"name.lower()")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the candidature states.
        Returns:
            The names of the candidature states.
        """
        return CandidatureStates.__members__.keys()

@unique
class CandidatureEmailSendStatus(Enum):
    """Status of the email sent to the applicant.
    """
    IN_PREPARATION = "candidature_email_send_status_in_preparation_value" # "In Preparation: The email is being prepared."
    SENT = "candidature_email_send_status_sent_value" # "Sent: The email has been sent."
    ERROR = "candidature_email_send_status_error_value" # "Error: An error occured while sending the email."


@unique
class CandidatureTypes(Enum) :
    """Types of candidatures.
    """
    ORDINARY = "candidature_types_ordinary_value" # "Ordinary: A candidature for an ordinary member."
    COOPERATOR = "candidature_types_cooperator_value" # "Cooperator: A candidature for a cooperator member."
    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the candidature type.
        Args:
            name: The name of the candidature type.
        Returns:
            The i18n id of the candidature type.
        """
        match name:
            case cls.ORDINARY.name :
                return "candidature_types_ordinary"
            case cls.COOPERATOR.name :
                return "candidature_types_cooperator"
            case cls.ORDINARY.value :
                return "candidature_types_ordinary_value"
            case cls.COOPERATOR.value :
                return "candidature_types_cooperator_value"
            case _ :
                # should never happen
                log.error(f"Unknown candidature type: {name}")
                return(f"name.lower()")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the candidature types.
        Returns:
            The names of the candidature types.
        """
        return CandidatureTypes.__members__.keys()

@unique
class VotingChoice(Enum) :
    """Voting choices.
    """
    YES = "vote_types_yes_value" # "Yes: The vote is positive."
    NO = "vote_types_no_value" # "No: The vote is negative."
    ABSTAIN = "vote_types_abstain_value" # "Abstain: The vote is neutral."

    @classmethod
    def get_i18n_id(cls, name:str) -> str:
        """Get the i18n id of the vote type.
        Args:
            name: The name of the vote type.
        Returns:
            The i18n id of the vote type.
        """
        match name:
            case cls.YES.name :
                return "vote_types_yes"
            case cls.NO.name :
                return "vote_types_no"
            case cls.ABSTAIN.name :
                return "vote_types_abstain"
            case cls.YES.value :
                return "vote_types_yes_value"
            case cls.NO.value :
                return "vote_types_no_value"
            case cls.ABSTAIN.value :
                return "vote_types_abstain_value"
            case _ :
                # should never happen
                log.error(f"Unknown vote type: {name}")
                return(f"vote_types_{name.lower()}")

    @staticmethod
    def get_names() -> List[str]:
        """Get the names of the candidature voting choice.
        Returns:
            The names of the voting choice.
        """
        return VotingChoice.__members__.keys()

@dataclass
class CandidatureEvent:
    """An event.
    """
    datetime:datetime # the datetime of the event
    function_name:str # the name of the function that triggered the event
    value_before:Any # the value of the candidature before the event
    value_after:Any # the value of the candidature after the event
    seed:str # the seed of the candidature at the moment of the event
    def __repr__(self):
        return f"<CandidatureEvent({self.datetime}, "\
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
        return iter((self.datetime, self.function_name, value_before, value_after, self.seed))

@dataclass
class CandidatureEmailEvent:
    """An email send event
    """
    datetime:datetime # the datetime of the event
    state:CandidatureEmailSendStatus # the state of the email
    function_name:str # the name of the function that triggered the event
    seed:str # the seed of the email send event

class Candidatures(PersistentMapping):
    """A mapping to store candidatures in the ZODB.
    Coulb be used as a singleton if all calls are made through get_instance.
    """
    _instance = None

    @staticmethod
    def get_instance(connection:Connection = None) -> Type['Candidatures']:
        """Get the singleton instance. Not thread safe !
        Args:
            connection: The ZODB connection, could be change for testing.
        Returns:
            The singleton instance.
        Raises:
            TypeError: The connection argument must be an instance of ZODB.Connection.Connection
        """
        if Candidatures._instance is not None:
            return Candidatures._instance

        # Check if a ZODB is provided
        if not isinstance(connection, Connection):
            raise TypeError("The connection argument must be an instance of ZODB.Connection.Connection")

        # check if root exists
        root = connection.root()
        if 'candidatures' not in root:
            connection.root()['candidatures'] = Candidatures()
            transaction.commit()
        Candidatures._instance = connection.root()['candidatures']
        return root['candidatures']

    def __init__(self):
        """Constructor.
        """
        super().__init__()
        self._monitored_candidatures = PersistentMapping()

    @property
    def monitored_candidatures(self)-> PersistentMapping:
        """ Get the monitored candidatures.
        A monitored candidature is a candidature that is not in DRAFT or APPROUVED or REFUSED state and needs to be monitored.
        For exemple, It could be necessary to send them a reminder email to the verifiers if the expiration date is approaching.
        Returns:
            The monitored candidatures.
        """
        return self._monitored_candidatures

def random_string(length:int, chars:str = string.ascii_lowercase + string.digits) -> str:
    """ Generate a random string of a given length.
    Could be overloaded for testing.
    Args:
        length: The length of the string.
        chars: The characters to use to generate the string.
    Returns:
        A random string.
    """
    return ''.join(random.choice(chars) for _ in range(length))

class CandidatureFunctions:
    """A class to store functions used by the Candidature class.
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
        return CandidatureFunctions.func_now()
    @staticmethod
    def uuid() -> str:
        """Get a unique identifier (UUID).
        Returns:
            A unique identifier (UUID).
        """
        return CandidatureFunctions.func_uuid()

class Candidature(Persistent):
    """A candidature in the ZODB.
    """

    __acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]

    def __init__(self, data = None):
        """    Initialize a new Candidature object.

        Args:
            data (Optional[Type]): Initial data for the candidature. Defaults to None.

        Attributes:
            _data (Type): The data for the candidature.
            _voters (List): A list to keep track of voters.
            _modifications (List[CandidatureEvent]): A list to record
                modifications, each entry is a dataclass containing the
                datetime, the function name, the previous value, the new value.
            _state (CandidatureStates): The current state of the candidature.
            _type (CandidatureTypes or None): The type of the candidature.
            _email (str or None): The email associated with the candidature.
            _votes (Dict): A dictionary to keep track of votes.
            _oid (str): A unique object identifier.
            _seed (str): A random string used to generate the OID.
            _email_send_status_history (List[CandidatureEmailEvent]): A list to record email send status history.
        Raises:
            RuntimeError: Raised if an instance already exists with same oid.

        """
        self._data = data
        self._voters = []
        self._state = CandidatureStates.DRAFT
        self._type = None
        self._email = None
        self._votes = {}
        self._seed = None
        self._email_send_status_history = []
        # get a unique object id
        self._oid = Candidature.generate_unique_oid()
        # get a random seed and record the creation
        self._modifications = []
        self._memorize_changes("__init__", None, self._state)

    def _memorize_changes(
        self, 
        function_name: Optional[str] = None, 
        previous_value: Optional[Any] = None, 
        new_value: Optional[Any] = None
        ) -> None:
        """Memorize changes to the candidature and generate a new seed.
        
        Args:
            function_name (Optional[str]): The name of the function that triggered the change. Defaults to "_change_seed".
            previous_value (Optional[Any]): The previous value of the candidature property. Defaults to None.
            new_value (Optional[Any]): The new value of the candidature property. Defaults to None.
        """
        function_name = function_name or "_change_seed"  # Fallback to "_change_seed" if function_name is None
        old_seed = self._seed or "None"  # Fallback to "None" if self._seed is None

        self._seed = random_string(SEED_LENGTH) 

        event = CandidatureEvent(
            datetime=CandidatureFunctions.now(), 
            function_name=function_name,
            value_before=previous_value,
            value_after=new_value,
            seed=self._seed
        )

        self._modifications.append(event)
        self._p_changed = True  # Mark the object as changed

    @property
    def seed(self)-> str:
        """ Get the seed of the candidature.
        Returns:
            The seed of the candidature.
        """
        return self._seed

    @property
    def state(self)-> CandidatureStates:
        """ Get the state of the candidature.
        Returns:
            The state of the candidature.
        """
        return self._state
    
    @state.setter
    def state(self, value:CandidatureStates):
        """ Set the state of the candidature.

        Args:
            value (CandidatureStates): The new state of the candidature.

        Raises:
            TypeError: The state must be an instance of CandidatureStates.
        """
        if not isinstance(value, CandidatureStates):
            raise TypeError("The state must be an instance of CandidatureStates.")
        
        old_state = self._state.name if self._state else "None"
        self._state = value
        self._memorize_changes("state", old_state, value.name)
    
    @property
    def type(self)-> CandidatureTypes:
        """ Get the type of the candidature.
        Returns:
            The type of the candidature.
        """
        return self._type
    
    @type.setter
    def type(self, value:CandidatureTypes):
        """ Set the type of the candidature.

        Args:
            value (CandidatureTypes): The new type of the candidature.

        Raises:
            TypeError: The type must be an instance of CandidatureTypes.
        """
        if not isinstance(value, CandidatureTypes):
            raise TypeError("The type must be an instance of CandidatureTypes.")
        
        old_type = self._type.name if self._type else "None"
        self._type = value
        self._memorize_changes("type", old_type, value.name)

    @property
    def email(self)-> str:
        """ Get the email of the candidature.
        Returns:
            The email of the candidature.
        """
        return self._email
    
    @email.setter
    def email(self, value:str):
        """ Set the email of the candidature.

        Args:
            value (str): The new email of the candidature.

        Raises:
            TypeError: The email must be a string.
        """
        if not isinstance(value, str):
            raise TypeError("The email must be a string.")
        
        old_email = self._email if self._email else "None"
        self._email = value
        self._memorize_changes("email", old_email, value)

    @property
    def modifications(self)-> List[CandidatureEvent]:
        """ Get the modifications of the candidature.
        Returns:
            A copy of modifications of the candidature as a list of CandidatureEvent.
        """
        return self._modifications.copy()
    
    @property
    def oid(self)-> str:
        """ Get the oid of the candidature.
        Returns:
            The oid of the candidature.
        """
        return self._oid

    @property
    def data(self)-> Type:
        """ Get the data of the candidature.
        Returns:
            The data of the candidature.
        """
        return self._data
    
    @data.setter
    def data(self, value:Type):
        """ Set the data of the candidature.

        Args:
            value (Type): The new data of the candidature.

        Raises:
            TypeError: The data must be a Type.
        """
        if not isinstance(value, Type):
            raise TypeError("The data must be a Type.")
        
        old_data = self._data if self._data else "None"
        self._data = value
        self._memorize_changes("data", old_data, value)

    @property
    def voters(self)-> [str]:
        """ Get the voters of the candidature.
        Returns:
            A copy of voters of the candidature.
        """
        return self._voters[:]
    
    @voters.setter
    def voters(self, value:[str]):
        """ Set the voters of the candidature.

        Args:
            value ([str]): The new voters of the candidature.

        Raises:
            TypeError: The voters must be a list.
        """
        if not isinstance(value, list) or not isinstance(value, tuple):
            raise TypeError("The voters must be a list or a tuple.")
        
        old_voters = self._voters if self._voters else "None"
        self._voters = value
        self._memorize_changes("voters", old_voters, value)
    
    @property
    def votes(self)-> {str: VotingChoice}:
        """ Get the votes of the candidature.
        Returns:
            A copy of votes of the candidature.
        """
        return self._votes.copy()
    
    @votes.setter
    def votes(self, value:{VotingChoice: int}):
        """ Set the votes of the candidature.

        Args:
            value ({VotingChoice: int}): The new votes of the candidature.

        Raises:
            TypeError: The votes must be a dict.
        """
        if not isinstance(value, dict):
            raise TypeError("The votes must be a dict.")
        
        old_votes = self._votes if self._votes else "None"
        self._votes = value
        self._memorize_changes("votes", old_votes, value)


    @staticmethod
    def generate_unique_oid(candidatures:Candidatures = None, max_retries:int = 10):
        """
        Generate a unique Object Identifier (OID) for a new Candidature object.

        This function tries to generate a unique OID by using the CandidatureFunctions.uuid function.
        It checks for uniqueness by looking into the existing `candidatures` mapping.

        Args:
            candidatures (Candidatures, optional): The mapping of existing candidatures to check for OID uniqueness. 
                                                Defaults to the singleton instance of the Candidatures class.
            max_retries (int, optional): Maximum number of attempts to generate a unique OID. Defaults to 10.

        Returns:
            str: A unique OID.

        Raises:
            ValueError: If a unique OID cannot be generated after `max_retries` attempts.
        """
        if candidatures is None:
            # get the singleton instance
            candidatures = Candidatures.get_instance()
        for _ in range(max_retries):
            oid = str(CandidatureFunctions.uuid())
            if oid not in candidatures:
                return oid
        raise ValueError(f"Failed to generate a unique OID after {max_retries} attempts.")

    @property
    def email_send_status_history(self)-> List[CandidatureEmailEvent]:
        """ Get the email send status history of the candidature.
        Returns:
            A copy of email send status history of the candidature.
        """
        return self._email_send_status_history.copy()    
    
    def add_email_send_status(self, value:CandidatureEmailSendStatus, procedure_name:str):
        """ Add an email send status to the candidature.
        Args:
            value (CandidatureEmailSendStatus): The new status of the email sent to the applicant.
            procedure_name (str): The name of the procedure used to send the email to the applicant.

        Raises:
            TypeError: The status must be an instance of CandidatureEmailSendStatus.
        """
        if not isinstance(value, CandidatureEmailSendStatus):
            raise TypeError("The status must be an instance of CandidatureEmailSendStatus.")
        old_status = self._email_send_status_history[-1].state if self._email_send_status_history else "None"

        # if the status is IN_PREPARATION, generate a new seed
        if value == CandidatureEmailSendStatus.IN_PREPARATION:
            email_seed = random_string(SEED_LENGTH)
        else:
            email_seed = self._email_send_status_history[-1].seed if self._email_send_status_history else "None"
        self._memorize_changes("add_email_send_status", old_status, value.name)

        
    

