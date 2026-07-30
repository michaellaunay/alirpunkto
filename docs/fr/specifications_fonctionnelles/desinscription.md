# Désinscription (démission d'un membre)

Implémente le scénario historique
[Démissionner](../specifications_historiques/Scénarios/Démissionner.md).

## Parcours nominal

1. Depuis **sa propre** page de profil, le membre suit « Désactiver mon
   compte ».
2. La page récapitule les **implications** : plus de connexion à la
   plateforme ni aux applications reliées ; conservation des données
   pendant la **Quarantaine** (180 jours par défaut, §3.4 des statuts,
   réglable par `QUARANTINE_PERIOD_DAYS`) puis effacement, seuls le
   pseudonyme, la date et le motif étant conservés ; rien ne se passe sans
   le lien de confirmation.
3. À la confirmation du formulaire, le membre passe à
   `PENDING_UNSUBSCRIPTION` et reçoit un courriel dont **le lien est la
   véritable confirmation** (validité : 7 jours). Si l'envoi échoue,
   l'état est restauré.
4. Au clic du lien : état `UNSUBSCRIBED`, compte **désactivé** dans
   l'annuaire (l'entrée est conservée — le pseudonyme et l'identité
   restent réservés pendant la Quarantaine), date d'effacement
   programmée, courriel d'adieu, session close. La connexion est
   désormais refusée.
5. Après la Quarantaine, la **purge** (tâche périodique, voir
   [09_taches_periodiques](../architecture/09_taches_periodiques.md))
   efface tout sauf le pseudonyme, la date et le motif, supprime l'entrée
   de l'annuaire et **informe l'ancien membre** que ses données ont bien
   été effacées.

## Scénarios alternatifs

- **Annulation** : tant que la demande est en attente, le profil propose
  « Annuler ma demande de désactivation » — l'état précédent est
  restauré.
- **Expiration** : une demande non confirmée sous 7 jours expire
  d'elle-même (vérification paresseuse au profil et au clic) ; le compte
  reste actif.
- **Lien re-cliqué** : idempotent — la page confirme simplement que le
  compte est désactivé.

## Garanties

- Un compte désactivé ne peut plus se connecter (garde à
  l'authentification).
- L'identité d'un démissionnaire ne peut pas se réinscrire pendant la
  Quarantaine (#54).
- Le membre quitte tous les groupes dynamiques à la désactivation (#148).
