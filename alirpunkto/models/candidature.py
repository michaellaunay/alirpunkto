# Description: Candidature model
#   A candidature is an object that represents a candidate's application.
# Creation date: 2023-07-22
# Author: Michaël Launay

from typing import Type, Tuple, List, Dict
from dataclasses import dataclass
from persistent.mapping import PersistentMapping
from pyramid.authorization import Allow, ALL_PERMISSIONS
from enum import Enum, unique
from ZODB.Connection import Connection
import transaction

# Constants
from alirpunkto.constants_and_globals import (
    _,
    log,
)

from alirpunkto.models.member import (
    Member,
    MemberStates
)

@unique
class CandidatureStates(Enum) :
    """States of candidatures.
    Beacause in python we can't herit from Enum, we have to redefine the DRAFT
    """
    # Draft: The application is in draft mode.
    DRAFT = "candidature_states_draft_value"
    # Email Validation: The state where the Applicant's email address is
    # awaiting validation.
    EMAIL_VALIDATION = "candidature_states_email_validation_value"
    # ConfirmedHuman: The Applicant's email address is verified, and humanity
    # proof is provided.
    CONFIRMED_HUMAN = "candidature_states_confirmed_human_value"
    # UniqueData: The Applicant has entered their personal identification data.
    UNIQUE_DATA = "candidature_states_unique_data_value"
    # Pending: After the submission of the application and while waiting for
    # verification by the verifiers.
    PENDING = "candidature_states_pending_value" 
    # Approved: The application has been accepted.
    APPROVED = "candidature_states_approved_value"
    # Refused: The application has been denied.
    REFUSED = "candidature_states_refused_value"

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
class Voter:
    """A voter.
    """
    email:str
    fullsurname:str
    vote:VotingChoice = None

class Candidature(Member):
    """A candidature in the ZODB.
    """

    __acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]

    def __init__(self, data = None):
        """    Initialize a new Candidature object.

        Args:
            data (Optional[Type]): Initial data for the candidature.
             Defaults to None.

        Attributes:
            _voters (List): A list to keep track of voters.
            _votes (Dict): A dictionary to keep track of votes.
            _challenge (Tuple[str, int]): A tuple containing the string math
             challenge and the solution in integer.
        Raises:
            RuntimeError: Raised if an instance already exists with same oid.

        """
        super().__init__(data)
        self._voters = []
        self._candidature_state = CandidatureStates.DRAFT
        self._votes = {}
        self._challenge = None
        # get a random seed and record the creation
        self._memorize_changes("Candidature.__init__", None, self._candidature_state)

    @property
    def candidature_state(self)-> CandidatureStates:
        """ Get the state of the candidature.
        Returns:
            The state of the candidature.
        """
        return self._candidature_state
    
    @candidature_state.setter
    def candidature_state(self, value:CandidatureStates):
        """ Set the state of the candidature.

        Args:
            value (CandidatureStates): The new state of the candidature.

        Raises:
            TypeError: The state must be an instance of CandidatureStates.
        """
        if not isinstance(value, CandidatureStates):
            raise TypeError(
                "The state must be an instance of CandidatureStates."
            )
        if value == CandidatureStates.APPROVED:
            self.member_state = MemberStates.REGISTRED
        old_candidature_state = self._candidature_state.name if self._candidature_state else "None"
        self._candidature_state = value
        self._memorize_changes("state", old_candidature_state, value.name)
    
    @property
    def challenge(self)-> Tuple[str, int]:
        """ Get the challenge of the candidature.
        Returns:
            The challenge of the candidature.
        """
        return self._challenge
    
    @challenge.setter
    def challenge(self, value:Dict[str, Tuple[str, int]]):
        """ Set the challenge of the candidature.

        Args:
            value (Dict[str, Tuple[str, int]]): The new challenge of the candidature.

        Raises:
            TypeError: The challenge must be a dict of tuple.
        """
        if not isinstance(value, dict):
            raise TypeError(
                "The challenge must be a dictionary with strings as keys and "
                "tuples as values."
            )
        
        old_challenge = self._challenge if self._challenge else "None"
        self._challenge = value
        self._memorize_changes("challenge", old_challenge, value)

    @property
    def voters(self)-> List[Voter]:
        """ Get the voters of the candidature.
        Returns:
            A copy of voters of the candidature.
        """
        return self._voters[:]
    
    @voters.setter
    def voters(self, value:list[Voter]):
        """ Set the voters of the candidature.

        Args:
            value ([Voter]): The new voters of the candidature.

        Raises:
            TypeError: The voters must be a list.
        """
        if not isinstance(value, list) and not isinstance(value, tuple):
            raise TypeError("The voters must be a list or a tuple.")
        
        old_voters = self._voters if self._voters else "None"
        self._voters = value
        self._memorize_changes("voters", old_voters, value)
    
    @property
    def votes(self)-> Dict[str, VotingChoice]:
        """ Get the votes of the candidature.
        Returns:
            A copy of votes of the candidature.
        """
        return self._votes.copy()
    
    @votes.setter
    def votes(self, value:Dict[VotingChoice, int]):
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

