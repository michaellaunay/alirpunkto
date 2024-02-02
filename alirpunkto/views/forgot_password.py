# description: forgot password view
# author: Michaël Launay
# date: 2023-06-15

from pyramid.view import view_config

from alirpunkto.utils import (
    is_not_a_valid_email_address,
    get_member_by_mail,
)

from alirpunkto.constants_and_globals import (
    _,
    log
)

@view_config(route_name='forgot_password', renderer='alirpunkto:templates/forgot_password.pt')
def forgot_password(request):
    """Forgot password view.
    Send an email to the user with a link to reset his password
    
    Args:
        request (pyramid.request.Request): the request
    """
    # 1) AlirPunkto displays the forgot_password.pt zpt to enter the mail 
    if 'submit' in request.POST:
        # 2) The user has entered his mail and validated
        mail = request.POST['mail']
        # 2.1) AlirPunkto checks that the mail is valid
        if err:= is_not_a_valid_email_address(mail, check_mx=False):
            log.warning('forgot_password: Invalid email address: {}'.format(mail[:512]))
            # 2.1.1) If not, AlirPunkto displays an error message
            request.session.flash(err["error"], 'error')
            # 2.1.2) Return to 1
            return err

        # 3) AlirPunkto checks that the mail exists in ldap
        members = get_member_by_mail(mail)
        if not members:
            # 3.1) If the mail does not exist, AlirPunkto displays a message indicating that if the user exists, he will receive an email
            request.session.flash(_('forget_email_in_member_list'), 'warning')
            # 3.2) End of the procedure
            return {"error":_('forget_email_in_member_list')}
        # 4) AlirPunkto retrieves information about the user from the ldap
        if len(members) > 1:
            log.warning('forgot_password: Multiple members found for mail: {}'.format(mail[:512]))
        member = members[0]
        pseudo = member['cn']
        uid = member['uid']
        # 5) AlirPunkto checks if there is an application for the user

        # 5.1) If not, AlirPunkto creates an application from the ldap information
        # 5.2) If yes, AlirPunkto retrieves the application and updates it with the ldap information (ldap priority)
        # 6) AlirPunkto generates a hashed password reset token
        # 7) AlirPunkto creates a password reset event and adds the token to it
        # 8) AlirPunkto creates a link to the application with the token
        # 9) AlirPunkto sends an email to the user with the link
        # 10) AlirPunkto displays a message indicating that the email has been sent (same message as 3.1)
        # 11) The user receives the email and clicks on the link
        # 11.1) If the link is invalid or expired, AlirPunkto displays an error message
        # 11.2) Return to 1
        # 12) AlirPunkto displays the forgot_password.pt zpt to enter the new password
        # 13) The user enters his new password and validates
        # 14) AlirPunkto checks that the password is valid and meets the security constraints
        # 14.1) If the password is not valid, AlirPunkto displays an error message



    # 2) L'utilisateur saisit son mail et valide
    # 3) AlirPunkto vérifie que le mail existe dans ldap
    # 3.1) Si le mail n'existe pas, AlirPunkto affiche un message indiquant que si l'utilisateur existe, il recevra un mail 
    # 3.2) Fin de la procédure
    # 4) AlirPunkto récupère les informations concernant l'utilisateur depuis le ldap
    # 5) AlirPunkto regarde s'il existe une candidature pour l'utilisateur
    # 5.1) Si non, AlirPunkto crée une candidature à partir des informations du ldap
    # 5.2) Si oui, AlirPunkto récupère la candidature et la met à jour avec les informations du ldap (priorité au ldap)
    # 6) AlirPunkto génère un token hashé de réinitialisation du mot de passe
    # 7) AlirPunkto crée un événement de réinitialisation du mot de passe et lui ajoute le token
    # 8) AlirPunkto crée un lien vers la candidature avec le token
    # 9) AlirPunkto envoie un mail à l'utilisateur avec le lien
    # 10) AlirPunkto affiche un message indiquant que le mail a été envoyé (même message que 3.1)
    # 11) L'utilisateur reçoit le mail et clique sur le lien
    # 11.1) Si le lien est invalide ou expiré, AlirPunkto affiche un message d'erreur
    # 11.2) Retour en 1
    # 12) AlirPunkto affiche la zpt forgot_password.pt de saisie du nouveau mot de passe
    # 13) L'utilisateur saisit son nouveau mot de passe et valide
    # 14) AlirPunkto vérifie que le mot de passe est valide et respecte les contraintes de sécurité
    # 14.1) Si le mot de passe n'est pas valide, AlirPunkto affiche un message d'erreur
    # 14.2) Retour en 12
    # 15) AlirPunkto met à jour le mot de passe dans le ldap
    # 16) AlirPunkto met à jour les événements de la candidature
    # 17) AlirPunkto affiche la zpt forgot_password.pt de confirmation de changement de mot de passe
    # 18) AlirPunkto envoie un mail à l'utilisateur pour le prévenir du changement de mot de passe
    return {}
