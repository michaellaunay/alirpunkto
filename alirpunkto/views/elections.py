"""
Elections Module

This module defines the ElectionsView class.
It is responsible for handling requests related to elections requiring active participation. 
The view provides functionalities like listing available elections, checking participation requirements, 
and possibly managing user interactions related to these elections.
"""

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from alirpunkto.utils import get_candidatures
# Import any other necessary modules or packages

@view_config(route_name='elections', renderer='alirpunkto:templates/elections.pt')
def elections_view(request):
    logged_in = request.params.get('logged_in', False)
    site_name = request.params.get('site_name', 'AlirPunkto')
    domain_name = request.params.get('domain_name', 'alirpunkto.org')
    username = request.params.get('username', "")
    elections = []
    user = request.session.get('user', None)
    if not user:
        return HTTPFound(location=request.route_url('login'))
    else :
        candidature = get_candidatures()
    return {"elections":elections}

