"""_summary_
Define the user model which is used to store users in the zodb database.
"""
from dataclasses import dataclass, asdict, field
from typing import Union
import json
from persistent import Persistent

@dataclass
class User(Persistent):
    """A user in the LDAP directory, stored in the ZODB database."""
    name: str
    email: str
    oid: str
    isActive: bool = True
    type: str = "ORDINARY"

    def __post_init__(self):
        super().__init__()  # Needed to initialize Persistent base class properties

    def to_json(self) -> str:
        """Return a json representation of the user."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: Union[dict, str]) -> 'User':
        """Create a User instance from json data.
        args:
            data (Union[dict, str]): the json data in string or dict format.
        return:
            User: the user created.
        """
        if isinstance(data, str):
            data = json.loads(data)
        return cls(**data)

    def __repr__(self):
        return f"<User name={self.name!r} email={self.email!r} oid={self.oid!r}>"
