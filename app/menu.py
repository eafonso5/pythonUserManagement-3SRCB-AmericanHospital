from fonctions_gestion import (
    creer_utilisateur, consulter_liste_utilisateurs, rechercher_utilisateur,
    modifier_utilisateur, supprimer_utilisateur, changer_mon_mot_de_passe,
    est_admin, consulter_profil
)


def afficher_menu_admin(user_connecte):
    """Affiche le menu destiné aux administrateurs."""

    # Affiche un en-tête indiquant le rôle et l'identité de l'utilisateur connecté
    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : ADMINISTRATEUR")
    print("=" * 60)

    # Affichage de toutes les options accessibles aux administrateurs
    print("\n1. Créer un nouvel utilisateur")
    print("2. Consulter la liste des utilisateurs")
    print("3. Rechercher un utilisateur")
    print("4. Modifier un utilisateur")
    print("5. Supprimer un utilisateur")
    print("6. Consulter mon profil")
    print("7. Changer mon mot de passe")
    print("8. Quitter")
    print("\n" + "=" * 60) 


def afficher_menu_user(user_connecte):
    """Affiche le menu destiné aux utilisateurs standard."""

    # En-tête filtré pour les Users avec options limitées
    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : USER")
    print("=" * 60)

    # Affichage des actions disponibles pour un utilisateur classique
    print("\n1. Consulter mon profil")
    print("2. Changer mon mot de passe")
    print("3. Quitter")
    print("\n" + "=" * 60)


def menu_administrateur(db, user_connecte):
    """Point d'entrée du menu administrateur.
       Boucle permettant d'exécuter les actions tant que l'utilisateur reste dans le menu."""

    while True:
        # On affiche systématiquement le menu avant chaque choix
        afficher_menu_admin(user_connecte)

        # Lecture du choix utilisateur
        choix = input("\nVotre choix : ").strip()
        
        # Gestion des actions via pattern matching (structure moderne Python)
        match choix:
            case "1":
                # Création d'un nouvel utilisateur
                creer_utilisateur(db, user_connecte)
        
            case "2":
                # Consultation de tous les comptes existants
                consulter_liste_utilisateurs(db, user_connecte)
        
            case "3":
                # Recherche ciblée dans les utilisateurs
                rechercher_utilisateur(db, user_connecte)
        
            case "4":
                # Modification d'un utilisateur existant
                modifier_utilisateur(db, user_connecte)
        
            case "5":
                # Suppression d'un compte
                supprimer_utilisateur(db, user_connecte)
        
            case "6":
                # Consultation des informations personnelles de l'administrateur
                consulter_profil(user_connecte)        
        
            case "7":
                # Changement du mot de passe personnel
                changer_mon_mot_de_passe(db, user_connecte)
        
            case "8":
                # Sortie propre du menu administrateur
                print("Au revoir !")
                break
            
            case _:
                # Gestion d’une saisie invalide
                print("\nChoix invalide. Veuillez réessayer.")


def menu_utilisateur(db, user_connecte):
    """Menu réservé aux utilisateurs simples."""

    while True:
        # Affiche l’interface dédiée aux Users
        afficher_menu_user(user_connecte)

        # Récupération du choix
        choix = input("\nVotre choix : ").strip()
        
        match choix:
            case "1":
                # Affiche uniquement les informations du compte connecté
                consulter_profil(user_connecte)
        
            case "2":
                # L'utilisateur peut modifier son propre mot de passe
                changer_mon_mot_de_passe(db, user_connecte)
            
            case "3":
                # Quitte proprement le menu utilisateur
                print("Au revoir !")
                break
            
            case _:
                # Erreur de saisie
                print("\nChoix invalide. Veuillez réessayer.")


def menu_principal(db, user_connecte):
    """Redirige l'utilisateur vers le menu adapté en fonction de son rôle."""

    # Un admin ou super admin est envoyé vers le menu complet
    if est_admin(user_connecte):
        menu_administrateur(db, user_connecte)

    # Les utilisateurs standards sont envoyés vers le menu simplifié
    else:
        menu_utilisateur(db, user_connecte)
