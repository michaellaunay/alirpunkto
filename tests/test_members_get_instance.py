"""Unit tests for ``Members.get_instance`` (audit finding 2.14).

The singleton cached a ``Members`` mapping bound to one ZODB connection and,
because the cache was checked before the connection argument, returned that
cached object for *every* subsequent call regardless of the connection passed.
A second connection thus reused an object bound to the first (or to a closed)
connection — a source of ConnectionStateError and stale reads. The fix always
rebinds to the connection that is passed in.
"""

from __future__ import annotations

import pytest
from ZODB import DB
from ZODB.MappingStorage import MappingStorage

from alirpunkto.models.member import Members


@pytest.fixture
def zodb():
    db = DB(MappingStorage())
    try:
        yield db
    finally:
        db.close()


def test_get_instance_returns_mapping_bound_to_the_connection(zodb):
    conn = zodb.open()
    try:
        members = Members.get_instance(connection=conn)
        assert members is conn.root()["members"]
        assert members._p_jar is conn
    finally:
        conn.close()


def test_get_instance_rebinds_to_each_connection(zodb):
    # Regression: once _instance was set, the cached (first-connection) object
    # was returned regardless of the connection passed, so a second connection
    # reused an object bound to the first.
    conn1 = zodb.open()
    m1 = Members.get_instance(connection=conn1)  # creates + commits 'members'
    conn2 = zodb.open()
    try:
        m2 = Members.get_instance(connection=conn2)
        assert m1._p_jar is conn1
        assert m2._p_jar is conn2               # not conn1's cached object
        assert m2 is conn2.root()["members"]
        assert m1 is not m2
    finally:
        conn1.close()
        conn2.close()


def test_get_instance_without_connection_returns_the_cached_mapping(zodb):
    conn = zodb.open()
    try:
        bound = Members.get_instance(connection=conn)
        assert Members.get_instance() is bound
    finally:
        conn.close()


def test_get_instance_without_connection_and_no_cache_raises():
    # reset_model_singletons (autouse) leaves Members._instance = None here.
    with pytest.raises(TypeError):
        Members.get_instance()


def test_get_instance_rejects_a_non_connection_argument():
    with pytest.raises(TypeError):
        Members.get_instance(connection=object())
