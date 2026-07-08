# Réinitialisation du mot de passe

> Statut : spécification fonctionnelle courante (remplace
> `RéinitialisationDuMotDePasse.md`).
> Module : `alirpunkto/views/forgot_password.py`.

## Déroulé

1. **Demande** (`/forgot_password`) — le membre saisit son adresse ou son
   pseudonyme. La réponse est identique que le compte existe ou non.
2. **Jeton** — le site génère un lien de réinitialisation contenant l'`oid`
   **chiffré** accompagné d'une **graine** ; l'événement est journalisé dans
   `email_send_status_history` du membre et le courriel part via
   `send_email_to_member` (envoi transactionnel).
3. **Retour** — au clic, le site déchiffre le jeton (`decrypt_oid`) et
   n'accepte la demande que si la graine correspond au **dernier** envoi
   journalisé : tout lien antérieur est invalidé par un nouvel envoi.
4. **Nouveau mot de passe** — saisie et confirmation (règles
   `is_valid_password`), puis écriture LDAP via `update_member_password`
   avec hachage `{SSHA}` ; rien n'est conservé en clair.

## Propriétés de sécurité

- pas d'énumération de comptes (réponse constante) ;
- lien à usage effectif unique (graine du dernier événement) ;
- le secret ne transite que chiffré dans l'URL et n'est jamais stocké en
  clair.

## Limites connues

- Le lien n'a pas d'expiration temporelle propre : il n'est invalidé que
  par un envoi ultérieur. Une échéance explicite serait une amélioration
  simple.
