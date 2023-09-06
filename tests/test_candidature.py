from alirpunkto.models.candidature import Candidature, CandidatureStates, CandidatureTypes, CandidatureFunctions, Candidatures, VotingChoice, CandidatureEvent
from pyramid import testing
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from ZODB.Connection import Connection
import random
from itertools import cycle

mocked_zodb = Mock(spec=Connection) # Mock the ZODB connection
mocked_zodb.root.return_value = {} # Mock the root of the ZODB database

# Mock the datetime function used in the Candidature class
CandidatureFunctions.func_now = lambda: datetime(2023, 1, 1)

def test_candidatures_singleton():
    candidatures = Candidatures.get_instance(connection=mocked_zodb)
    assert candidatures is Candidatures.get_instance(connection=mocked_zodb)
    assert candidatures is mocked_zodb.root()['candidatures']

def test_candidature_init():

    candidatures = Candidatures.get_instance(connection=mocked_zodb)
    candidature = Candidature()
    seed = candidature.seed
    assert candidature.state == CandidatureStates.DRAFT
    assert candidature.seed is not None
    assert isinstance(seed, str)
    assert candidature.oid is not None
    assert len(candidature.modifications) == 1
    assert candidature.modifications[0] == CandidatureEvent(datetime(2023, 1, 1), CandidatureStates.DRAFT, seed)

def test_candidature_state():
    candidatures = Candidatures.get_instance(connection=mocked_zodb)
    candidature = Candidature()
    initial_state = candidature.state
    candidature.state = CandidatureStates.EMAIL_VALIDATION
    assert candidature.state == CandidatureStates.EMAIL_VALIDATION
    assert len(candidature.modifications) == 2
    assert candidature.get_previous_state() == initial_state

def test_candidature_rollback():
    candidatures = Candidatures.get_instance(connection=mocked_zodb)
    candidature = Candidature()
    initial_state = candidature.state # Normally DRAFT
    initial_seed = candidature.seed
    candidature.state = CandidatureStates.EMAIL_VALIDATION
    assert candidature.state == CandidatureStates.EMAIL_VALIDATION
    assert len(candidature.modifications) == 2
    assert candidature.seed != initial_seed
    candidature.rollback()
    assert candidature.state == initial_state
    assert candidature.seed == initial_seed
    assert len(candidature.modifications) == 1

def test_candidature_uuid():
    candidatures = Candidatures.get_instance(connection=mocked_zodb)
    POPULATION = 5
    tries = [0, 2, 0, 0, 3, 3, 2, 3, 2, 0, 0, 0, 5, 5, 2, 0, 0, 4, 1]  # A pseudo random list of integers between 0 and POPULATION
    # Can be generated with the following code:
    # references = set(range(0,POPULATION))
    # # until the tries list contains one occurence of each references items
    # while set(tries).intersection(references) != references:
    #     tries.append(random.randint(0,POPULATION))
    our_uuid = cycle(tries)
    CandidatureFunctions.func_uuid = lambda: f"test{next(our_uuid):0>5}"
    # Because we create exact POPULATION candidatures, we are sure that the uuid will be unique
    # Populating the candidatures
    for indice in range(0, POPULATION):
        candidature = Candidature()
        candidatures[candidature.oid] = candidature

    
# @TODO: test candidature functions
