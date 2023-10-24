"""_summary_
Define the user model which is used to store users in the zodb database.
"""
# description: User model

from persistent import Persistent
from pyramid.security import Allow, ALL_PERMISSIONS
from ldap3 import Connection
import json


# User class
class User(Persistent):
    """A user in the LDAP directory."""

    def __init__(self, name:str, email:str, oid:str) -> None:
        """Create a user from the LDAP directory.
        attr:
            name (str): the name of the user
            email (str): the email of the user
            oid (str): the oid of the user, same as his candidature oid
        """
        self.name = name
        self.email = email
        self.oid = oid

    @classmethod
    def create_user(cls, name:str, email:str, oid:str) -> 'User':
        """Create a user from the LDAP directory.
        attr:
            name (str): the name of the user
            email (str): the email of the user
            oid (str): the oid of the user, same as his candidature oid
        return:
            User: the user created
        """
        return cls(name, email, oid)

    def __repr__(self):
        return f"<User {self.name=!r} {self.email=!r} {self.oid=!r}>"
    
    def toJSON(self):
        """Return a json representation of the user
        """
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)
    
  
    # define iterable
    def __iter__(self):
        return iter([self.name, self.email, self.oid])
    
    @classmethod
    def from_json(cls, data, request = None):
        """Create a User instance from json data

        """
        return cls(data['name'], data['email'], data['oid'])

