from alirpunkto.models.member import MemberStates, MemberTypes, Members, MemberDataEvent, MemberDataFunctions
from alirpunkto.models.candidature import (Candidature, CandidatureStates,
        VotingChoice)
from datetime import datetime
from unittest.mock import Mock, patch
from ZODB.Connection import Connection
from itertools import cycle

mocked_zodb = Mock(spec=Connection) # Mock the ZODB connection
mocked_zodb.root.return_value = {} # Mock the root of the ZODB database

# Mock the datetime function used in the Candidature class
MemberDataFunctions.func_now = lambda: datetime(2023, 1, 1)

def test_candidatures_singleton():
    candidatures = Members.get_instance(connection=mocked_zodb)
    assert candidatures is Members.get_instance(connection=mocked_zodb)
    assert candidatures is mocked_zodb.root()['members']

def test_candidature_init():
    Members.get_instance(connection=mocked_zodb)
    candidature = Candidature()
    assert candidature.candidature_state == CandidatureStates.DRAFT
    seed = candidature.seed
    assert seed is not None
    assert isinstance(candidature.seed, str)
    assert candidature.oid is not None
    assert len(candidature.modifications) == 2
    old_seed=candidature.modifications[0].seed
    assert old_seed != seed != None
    assert candidature.modifications[0] == MemberDataEvent(
        datetime(2023, 1, 1), "__init__", None, MemberStates.DRAFT, old_seed)
    assert candidature.modifications[1] == MemberDataEvent(
        datetime(2023, 1, 1), "Candidature.__init__", None, CandidatureStates.DRAFT, seed)

def test_candidature_state():
    Members.get_instance(connection=mocked_zodb)
    candidature = Candidature()
    initial_state = candidature.candidature_state
    candidature.candidature_state = CandidatureStates.EMAIL_VALIDATION
    assert candidature.candidature_state == CandidatureStates.EMAIL_VALIDATION
    assert len(candidature.modifications) == 3
    assert candidature.modifications[-1].function_name == "state"
    assert candidature.modifications[-1].value_before == initial_state.name
    assert candidature.modifications[-1].value_after == CandidatureStates.EMAIL_VALIDATION.name
    assert candidature.modifications[-1].seed == candidature.seed


def test_candidature_uuid():
    candidatures = Members.get_instance(connection=mocked_zodb)
    tries = [0, 2, 0, 0, 3, 3, 2, 3, 2, 0, 0, 0, 5, 5, 2, 0, 0, 4, 1]  # A pseudo random list of integers between 0 and POPULATION
    # Can be generated with the following code:
    # POPULATION = 6
    # references = set(range(0,POPULATION))
    # # until the tries list contains one occurence of each references items
    # while set(tries).intersection(references) != references:
    #     tries.append(random.randint(0,POPULATION))
    our_uuid = cycle(tries)
    MemberDataFunctions.func_uuid = lambda: f"test{next(our_uuid):0>5}"
    unique_uuids = set([MemberDataFunctions.func_uuid() for x in range(0,len(tries))])
    # Because we create exact POPULATION candidatures, we are sure that the uuid will be unique
    # Populating the candidatures
    for indice in range(0, len(unique_uuids)):
        candidature = Candidature()
        candidatures[candidature.oid] = candidature
    # Ensure uniqueness of Candidature UUIDs
    for uuid in unique_uuids:
        assert uuid in candidatures

    
# @TODO: test candidature functions
