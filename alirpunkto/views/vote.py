# description: Login view
# author: Michaël Launay
# date: 2023-10-27

import datetime
import logging
from typing import Union
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from .. import _
from ..models.users import User
from ..models.candidature import (
    Candidature,
    VotingChoice,
    CandidatureEmailSendStatus
)
from ..utils import (
    get_candidatures,
    send_confirm_validation_email,
    send_candidature_state_change_email
)
from logging import getLogger

log = getLogger('alirpunkto')

@view_config(route_name='vote', renderer='alirpunkto:templates/vote.pt')
def login_view(request):
    """Vote view.

    Args:
        request (pyramid.request.Request): the request
    """
    logged_in = request.session['logged_in'] if 'logged_in' in request.session else False
    user = request.session['user'] if 'user' in request.session else None
    if not logged_in or not user:
        # redirect to login page
        request.session['redirect_url'] = request.current_route_url()
        return HTTPFound(location=request.route_url('login'))
    user = User.from_json(user)
    site_name = request.session['site_name']
    username = user.name
    oid = request.session['oid'] if 'oid' in request.session else request.params.get('oid', "")
    if oid and 'oid' not in request.session:
        request.session['oid'] = oid
    canditures = get_candidatures(request)
    if oid not in canditures:
        return {'error': _('invalid_oid'), 'site_name': site_name}
    candidature = canditures[oid]

    voter = None
    for v in candidature.voters:
        if v.email == user.email:
            voter = v
            break
    if not voter:
        return {'error': _('not_voter'), 'site_name': site_name}
    #@TODO check if the user can vote (if time is not passed )
    pass
    # Get the user's vote from the form
    if 'submit' in request.params:
        vote = request.POST.get('vote')
        if vote not in VotingChoice.get_names():
            request.session.flash('Invalid voting choice!', 'error')
            return HTTPFound(location=request.route_url('voting_page'))  # Redirect back to voting page
        
        voter.vote = vote

        transaction = request.tm
        # Save the vote
        transaction.commit()
        # check if all of the voter have voted
        if all([v.vote for v in candidature.voters]):
            # send email to the candidature owner
            count = [v.vote for v in candidature.voters].count(VotingChoice.YES.name)
            if count > len(candidature.voters) / 2:
                candidature.status = Candidature.Status.ACCEPTED
                transaction.commit()
                # send email to the candidature owner
                email_template = "send_candidature_approuved_email"
                
            else:
                candidature.status = Candidature.Status.REJECTED
                transaction.commit()
                email_template = "send_candidature_rejected_email"
            # send email to the candidature owner
            send_candidature_state_change_email(
                request,
                candidature,
                email_template
            )
            try:
                candidature.add_email_send_status(CandidatureEmailSendStatus.SENT, email_template)
                transaction.commit()
            except Exception as e:
                log.error(f"Error while sending email to the candidature owner: {e}")
                candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, email_template)
                send_result = send_confirm_validation_email(request, candidature)
                if 'error' in send_result:
                    candidature.add_email_send_status(CandidatureEmailSendStatus.ERROR, "send_confirm_validation_email")
                else:
                    transaction.commit()

        #@TODO if date is passed, compute the result with the votes

        #@TODO send email to the candidature owner

    return {
        'logged_in': True if user else False,
        'site_name': site_name,
        'user': username,
        'candidature': candidature,
        'VotingChoice': VotingChoice
    }
