# Projet python 3ème année SRC - Développement d’un outil de Gestion des Utilisateurs

## Membres du groupe : 
- Enzo AFONSO
- Raphael HOUNDJO
- Benjamin JUPILLE

## Analyse du sujet

### Demandes :
- Créer de nouveaux Utilisateurs selon les profils et les droits définis
- Définir les règles de gestion et de sécurité des login/pwd (Login : contraction
de la première lettre du prénom et du nom utilisateur (non composé), (PWD :
génération aléatoire et hashage avant sauvegarde persistante, durée de
validité, ...)
- Modifier/supprimer un utilisateur/un admin.
- Consulter la liste des utilisateurs/des admins.
- Rechercher un utilisateur/un admin particulier.
- Stocker les données dans un dictionnaire/liste ou dans un fichier CSV ou dans
une base de données.
- Permettre les accès aux divers admins (pas les patients) via une
authentification contrôlée.

### Approche :

- Création d'une classe User et de SubClasses pour normalisation des champs
- Création / Sécurisation des mots de passes avec un librairie externe (bcrypt)
- Création et utilisation d'une base de données sqlite
- Fonctions de consultation, de modification et de recherche des utilisateurs via la BDD
- Authentification lors de l'utilisation de fonctions

### Librairies :
- sqlalchemy : librairie intégrée pour la gestion BDD