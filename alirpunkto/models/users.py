"""_summary_
Define the user model which is used to store users in the zodb database.
"""
# description: User model

from persistent import Persistent
from pyramid.security import Allow, ALL_PERMISSIONS
from ldap3 import Connection


# User class
class User(Persistent):
    """A user in the LDAP directory."""

    def __init__(self, name, email):
        self.name = name
        self.email = email

    @classmethod
    def create_user(cls, name:str, email:str) -> 'User':
        """Create a user from the LDAP directory.
        """
        return cls(name, email)

    def __repr__(self):
        return f"<User {self.name=!r} {self.email=!r}>"

