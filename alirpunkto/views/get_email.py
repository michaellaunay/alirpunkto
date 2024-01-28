# Definition of the get_email view
# description: this view return the localyze email corresponding to the email parameter
# author: Michaël Launay
# date: 2024-01-26
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from .. import _
from ..models.users import User

from ..utils import (
    get_local_template,
    render_to_response
)
from pyramid.i18n import get_localizer
from logging import getLogger

log = getLogger('alirpunkto')

@view_config(route_name='get_email', renderer = 'string')
def get_email(request):
    """Get the email content from an id.

    Args:
        request (pyramid.request.Request): the request
    """
    logged_in = request.session.get('logged_in', False)
    user_json = request.session.get('user', None)
    if not logged_in or not user_json:
        # redirect to login page
        request.session['redirect_url'] = request.current_route_url()
        return HTTPFound(location=request.route_url('login'))
    user = User.from_json(user_json)
    site_name = request.session['site_name']
    email_id = request.params['email_id']
    link = request.session['link'] if 'link' in request.session else None

    template_name = (email_id + ".pt") if email_id else None
    if not template_name:
        log.error(f"get_email : Error while getting the template name from the email id {email_id}")    
        return None
    try:
        template_path = get_local_template(request, "locale/{lang}/LC_MESSAGES/"+template_name)
    except:
        log.error(f"get_email : Error while getting the template {template_name}")
        return None
    template_vars = {
        'site_name': site_name,
        'user': user,
        'link': link,
        'site_name': site_name,
    } 
    try:
        text_body = render_to_response(
            template_path,
            request=request,
            value={**template_vars, "textual":True}
        ).text
    except:
        log.error(f"get_email : Error while rendering the template {template_name}")
        return None
    # Return the email content as text
    return text_body