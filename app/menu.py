from fonctions_gestion import (creer_utilisateur, consulter_liste_utilisateurs,rechercher_utilisateur, modifier_utilisateur,supprimer_utilisateur, changer_mon_mot_de_passe,est_admin, consulter_profil)


def afficher_menu_admin(user_connecte):
    """Affiche le menu administrateur"""
    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : ADMINISTRATEUR")
    print("=" * 60)
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
    """Affiche le menu utilisateur standard"""
    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : USER")
    print("=" * 60)
    print("\n1. Consulter mon profil")
    print("2. Changer mon mot de passe")
    print("3. Quitter")
    print("\n" + "=" * 60)


def menu_administrateur(db, user_connecte):
    """Boucle du menu administrateur"""
    while True:
        afficher_menu_admin(user_connecte)
        choix = input("\nVotre choix : ").strip()
        
        match choix:
            case "1":
                creer_utilisateur(db, user_connecte)
        
            case "2":
                consulter_liste_utilisateurs(db)
        
            case "3":
                rechercher_utilisateur(db)
        
            case "4":
                modifier_utilisateur(db)
        
            case "5":
                supprimer_utilisateur(db)
        
            case "6":
                consulter_profil(user_connecte)        
        
            case "7":
                changer_mon_mot_de_passe(db, user_connecte)
        
            case "8":
                print("Au revoir !")
                break
            
            case _:
                print("\nChoix invalide. Veuillez réessayer.")        


def menu_utilisateur(db, user_connecte): 
    """Boucle du menu utilisé par les patients"""
    while True:
        afficher_menu_user(user_connecte)
        choix = input("\nVotre choix : ").strip()
        
        match choix:
            case "1":
                consulter_profil(user_connecte)
        
            case "2":
                changer_mon_mot_de_passe(db, user_connecte)
            
            case "3":
                print("Au revoir !")
                break
            
            case _:
                print("\nChoix invalide. Veuillez réessayer.")


def menu_principal(db, user_connecte):
    """Redirige vers le bon menu selon le rôle de l'utilisateur"""
    if est_admin(user_connecte):
        menu_administrateur(db, user_connecte)
    else:
        menu_utilisateur(db, user_connecte)