# Description: Candidature model
#   A candidature is an object that represents a candidate's application.
# Creation date: 2023-07-22
# Author: Michaël Launay

from persistent import Persistent
from datetime import datetime
from pyramid.security import Allow, ALL_PERMISSIONS

# Candidature class
class Candidature(Persistent):
    """A candidature in the LDAP directory."""

    __acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]

    def __init__(self, data):
        self.data = data
        self.voters = []
        self.submission_date = datetime.now()
        self.status = "pending"
        self.votes = {}
