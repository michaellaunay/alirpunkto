# Definition of the get_email view
# description: this view return the localyze email corresponding to the email parameter
# author: Michaël Launay
# date: 2024-01-26
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPBadRequest
from .. import _
from ..models.users import User
from ..utils import (
    get_local_template,
    render_to_response
)
from pyramid.i18n import get_localizer
from logging import getLogger
from functools import lru_cache
from typing import Set
import re
# Compile the regular expression for reuse
injection_pattern = re.compile(r'eval\(|exec\(|__import__')

log = getLogger('alirpunkto')

@lru_cache(maxsize=128)
def extract_zpt_variables(file_path: str) -> Set[str]:
    """
    Extract variables from a ZPT file, including those used in TAL expressions.

    Args:
        file_path (str): The path to the ZPT file.

    Returns:
        set: A set of unique variable names found in the ZPT file.
    """
    variable_pattern = r'\$\{([^}]+)\}'
    tal_pattern = r'tal:[a-zA-Z]+="([^"]+)"'
    variables = set()

    try:
        with open(file_path, 'r') as file:
            for line in file:
                # Extract variables in ${...}
                dollar_matches = re.findall(variable_pattern, line)
                for match in dollar_matches:
                    variable_name = match.split('|')[0].split('/')[0].strip()
                    variables.add(variable_name)
                
                # Extract variables in tal: attributes
                tal_matches = re.findall(tal_pattern, line)
                for tal_match in tal_matches:
                    # Splitting by spaces as TAL expressions can contain multiple statements
                    tal_vars = tal_match.split()
                    for tal_var in tal_vars:
                        # Extract the variable name before any semicolon or pipe if present
                        variable_name = tal_var.split(';')[0].split('|')[0].strip()
                        variables.add(variable_name)

    except FileNotFoundError:
        print(f"File not found: {file_path}")

    return variables

@view_config(route_name='get_email', renderer = 'string')
def get_email(request):
    """Get the email content from an id.

    Args:
        request (pyramid.request.Request): the request
    """
    # Check for code injection in URL parameters
    if any("python" in value or injection_pattern.search(value) for value in request.params.values()):
        log.error("Potential code injection attempt detected.")
        return HTTPBadRequest("Invalid request parameters")
    
    # Check if the user is logged in
    logged_in = request.session.get('logged_in', False)
    user_json = request.session.get('user', None)
    if not logged_in or not user_json:
        # Redirect to the login page if not logged in
        request.session['redirect_url'] = request.current_route_url()
        return HTTPFound(location=request.route_url('login'))

    user = User.from_json(user_json)
    site_name = request.registry.settings.get('site_name')
    email_id = request.params.get('email_id', None)
    link = request.session.get('link', None)

    template_name = f"{email_id}.pt" if email_id else None
    if not template_name:
        log.error(f"Error getting the template name from email ID {email_id}")
        return HTTPBadRequest("Invalid Email ID")

    try:
        template_path = get_local_template(
            request,
            "locale/{lang}/LC_MESSAGES/" + template_name
        )
        expected_variables = extract_zpt_variables(template_path.abspath())
    except Exception as e:
        log.error(f"Error getting the template {template_name}: {e}")
        return HTTPBadRequest("Template resolution error")

    # Construct template variables from URL parameters
    template_vars = {var: request.params.get(var, None) 
        for var in expected_variables if var in request.params}
    template_vars.update({'site_name': site_name, 'user': user, 'link': link})

    try:
        text_body = render_to_response(
            template_path,
            request=request,
            value={**template_vars, "textual": True}
        ).text
    except Exception as e:
        log.error(f"Error rendering the template {template_name}: {e}")
        return HTTPBadRequest("Error rendering email content")

    # Return the email content as text
    return text_body