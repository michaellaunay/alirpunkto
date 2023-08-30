# Description: Candidature model
#   A candidature is an object that represents a candidate's application.
# Creation date: 2023-07-22
# Author: Michaël Launay

from typing import Type, Callable, Tuple, List
from persistent import Persistent
from persistent.mapping import PersistentMapping
from datetime import datetime
from pyramid.security import Allow, ALL_PERMISSIONS
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

class Candidatures(PersistentMapping):
    """A singleton mapping of candidatures.
    """
    _instance = None

    @staticmethod
    def get_instance(zodb:Connection = None) -> Type['Candidatures']:
        """Get the singleton instance. Not thread safe !
        Args:
            zodb: The ZODB connection, could be change for testing.
        Returns:
            The singleton instance.
        Raises:
            TypeError: The zodb argument must be an instance of ZODB.Connection.Connection
        """
        # Check if singleton is allready store in a ZODB
        if Candidatures._instance is not None:
            return Candidatures._instance
        # Check if a ZODB is provided
        if zodb:
            if not isinstance(zodb, Connection):
                raise TypeError("The zodb argument must be an instance of ZODB.Connection.Connection")
            root = zodb.root()
            if 'candidatures' not in root:
                root['candidatures'] = Candidatures()
                transaction.commit()
                # if successfull, store the singleton in the class
                Candidatures._instance = root['candidatures']
            return Candidatures._instance

        else:
            raise ValueError("The zodb argument must be provided the first time.")
    
    def set_instance(instance:Type['Candidatures']):
        """Set the singleton instance. Not thread safe !
        Args:
            instance: The singleton instance.
        Raises:
            TypeError: The instance argument must be an instance of Candidatures
        """
        if instance is Candidatures._instance:
            return
        if not isinstance(instance, Candidatures):
            raise TypeError("The instance argument must be an instance of Candidatures")
        if Candidatures._instance is not None and instance is not Candidatures._instance:
            raise RuntimeError("Candidatures is a singleton, use Candidatures.set_instance(...) once at the beginning.")
        Candidatures._instance = instance

    def __init__(self):
        """Constructor.
        """
        if Candidatures._instance is not None:
            raise RuntimeError("Candidatures is a singleton, use Candidatures.get_instance().")
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
            _modifications (List[Tuple[datetime, str]]): A list to record modifications, each entry is a tuple 
                                                            containing the datetime and the modification message.
            _state (CandidatureStates): The current state of the candidature.
            _type (CandidatureTypes or None): The type of the candidature.
            _email (str or None): The email associated with the candidature.
            _votes (Dict): A dictionary to keep track of votes.
            _oid (str): A unique object identifier.

        Raises:
            RuntimeError: Raised if an instance already exists with same oid.

        """
        self._data = data
        self._voters = []
        self._modifications = [(CandidatureFunctions.now(), "Creation")]
        self._state = CandidatureStates.DRAFT
        self._type = None
        self._email = None
        self._votes = {}
        self._seed = None
        # get a random seed
        self._change_seed()
        # get a unique object id
        self._oid = Candidature.generate_unique_oid()
    
    def _change_seed(self):
        """Change the seed of the candidature.
        """
        old_seed = self._seed if self._seed else "None"
        self._seed = random_string(SEED_LENGTH)
        self._modifications.append((CandidatureFunctions.now(), f"seed:{old_seed} -> {self._seed}"))
        self._p_changed = True # mark the object as changed

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
        self._modifications.append((CandidatureFunctions.now(), f"state:{old_state} -> {value.name}"))
        self._change_seed()
    
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
        self._modifications.append((CandidatureFunctions.now(), f"type:{old_type} -> {value.name}"))
        self._change_seed()

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
        self._modifications.append((CandidatureFunctions.now(), f"email:{old_email} -> {value}"))
        self._change_seed()

    @property
    def modifications(self)-> List[Tuple[datetime, str]]:
        """ Get the modifications of the candidature.
        Returns:
            A copy of modifications of the candidature.
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
        self._modifications.append((CandidatureFunctions.now(), f"data:{old_data} -> {value}"))
        self._change_seed()

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
        self._modifications.append((CandidatureFunctions.now(), f"voters:{old_voters} -> {value}"))
        self._change_seed()
    
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
        self._modifications.append((CandidatureFunctions.now(), f"votes:{old_votes} -> {value}"))
        self._change_seed()

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

