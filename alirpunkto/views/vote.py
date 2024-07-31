# description: Login view
# author: Michaël Launay
# date: 2023-10-27

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from alirpunkto.models.users import User
from alirpunkto.models.candidature import (
    VotingChoice,
    CandidatureStates
)
from alirpunkto.models.member import (
    EmailSendStatus,
)
from alirpunkto.utils import (
    get_candidatures,
    send_confirm_validation_email,
    send_candidature_state_change_email,
    register_user_to_ldap
)

from alirpunkto.constants_and_globals import (
    _,
    log
)

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
    domain_name = request.session['domain_name']
    username = user.name
    oid = request.session['oid'] if 'oid' in request.session else request.params.get('oid', "")
    if oid and 'oid' not in request.session:
        request.session['oid'] = oid
    canditures = get_candidatures(request)
    if oid not in canditures:
        return {
            'error': _('invalid_oid'),
            'site_name': site_name,
            'domain_name': domain_name
            }
    candidature = canditures[oid]

    voter = None
    for v in candidature.voters:
        if v.oid == user.oid:
            voter = v
            break
    if not voter:
        return {
            'error': _('not_voter'),
            'site_name': site_name,
            'domain_name': domain_name
        }
    #@TODO check if the user can vote (if time is not passed )
    pass

    # Get the user's vote from the form
    if 'submit' in request.params:
        vote = request.POST.get('vote')
        if vote not in VotingChoice.get_names():
            return {
                'error': _('Invalid voting choice!'),
                'message': _('not_voter'),
                'site_name': site_name,
                'domain_name': domain_name
            }       
        voter.vote = vote

        transaction = request.tm
        # Save the vote
        transaction.commit()
        # check if all of the voter have voted
        if all([v.vote for v in candidature.voters]):
            # send email to the candidature owner
            count_yes = [v.vote for v in candidature.voters].count(VotingChoice.YES.name)
            count_no = [v.vote for v in candidature.voters].count(VotingChoice.NO.name)
            if count_yes > count_no:
                candidature.candidature_state = CandidatureStates.APPROVED
                register_user_to_ldap(request, candidature, candidature.data.password)
                candidature.add_email_send_status(
                    EmailSendStatus.IN_PREPARATION, 
                    "send_candidature_approuved_email"
                )
                transaction.commit()
                # send email to the candidature owner
                email_template = "send_candidature_approuved_email"
            else:
                candidature.candidature_state = CandidatureStates.REJECTED
                candidature.add_email_send_status(
                    EmailSendStatus.IN_PREPARATION, 
                    "send_candidature_rejected_email"
                )
                transaction.commit()
                email_template = "send_candidature_rejected_email"
            # send email to the candidature owner
            send_candidature_state_change_email(
                request,
                candidature,
                email_template
            )
            try:
                candidature.add_email_send_status(EmailSendStatus.SENT, email_template)
                transaction.commit()
            except Exception as e:
                log.error(f"Error while sending email to the candidature owner: {e}")
                # Explicitly abort the transaction to ensure consistency
                request.tm.abort()
                candidature.add_email_send_status(EmailSendStatus.ERROR, email_template)
                # Return error message
                return {
                    'error': _('error_sending_voting_result_email'),
                    'logged_in': True if user else False,
                    'site_name': site_name,
                    'domain_name': domain_name,
                    'user': username,
                    'candidature': candidature,
                    'VotingChoice': VotingChoice,
                    'vote': voter.vote,
                    'registered_vote': True
                }

        return {
            'logged_in': True if user else False,
            'site_name': site_name,
            'domain_name': domain_name,
            'user': username,
            'candidature': candidature,
            'VotingChoice': VotingChoice,
            'vote': voter.vote,
            'registered_vote': True
        }

        #@TODO if date is passed, compute the result with the votes

        #@TODO send email to the candidature owner

    return {
        'logged_in': True if user else False,
        'site_name': site_name,
        'domain_name': domain_name,
        'user': username,
        'candidature': candidature,
        'VotingChoice': VotingChoice,
        'vote': voter.vote if voter.vote else '',
        'registered_vote': False
    }
