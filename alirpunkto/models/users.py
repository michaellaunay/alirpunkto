"""_summary_
Define the user model which is used to store users in the zodb database.
"""
# description: User model
from typing import Union
from persistent import Persistent
import json


# User class
class User(Persistent):
    """A user in the LDAP directory."""
    _admin_user = None
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
    
    def to_json(self):
        """Return a json representation of the user
        """
        return json.dumps({'name': self.name, 'email': self.email, 'oid': self.oid})
 
    @classmethod
    def from_json(cls, data:dict):
        """Create a User instance from json data

        """
        return cls(data['name'], data['email'], data['oid'])