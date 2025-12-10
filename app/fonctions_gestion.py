from classes import User
from datetime import datetime, timedelta

# Rôles disponibles dans le système
ROLES_DISPONIBLES = [
    "User",
    "Admin",
    "Super Admin"
]

VILLES_DISPONIBLES = [
    "Paris",
    "Marseille",
    "Rennes",
    "Grenoble"
]

def est_entier(valeur): # Vérifie si une valeur est un entier
    try:
        int(valeur)
        return True
    except ValueError:
        return False
    
def est_superadmin(user):
    """Vérifie si l'utilisateur a un rôle d'administrateur"""
    return user.Role == "Super Admin"

def est_admin(user):
    """Vérifie si l'utilisateur a un rôle d'administrateur"""
    return user.Role == "Super Admin" or user.Role == "Admin"

def creer_utilisateur(db,user_connecte):
    """Crée un nouvel utilisateur (réservé aux admins)"""
    print("\n=== CRÉATION D'UN NOUVEL UTILISATEUR ===")
    
    # Saisie des informations
    nom = input("Nom : ").strip()
    if not nom:
        print("Erreur : Le nom ne peut pas être vide.")
        return
    
    prenom = input("Prénom : ").strip()
    if not prenom:
        print("Erreur : Le prénom ne peut pas être vide.")
        return
    
    # Listing des rôles
    print("\nRôles disponibles :")
    if est_superadmin(user_connecte):
        roles_a_afficher = ROLES_DISPONIBLES[:2]  # Super Admins auront tous les rôles d'affichés, sauf Super Admin
        for i, role in enumerate(roles_a_afficher, 1):
            print(f"{i}. {role}")
    elif est_admin(user_connecte):
        roles_a_afficher = ROLES_DISPONIBLES[:1]  # Admins auront seulement "Utilisateur" d'affiché
        for i, role in enumerate(roles_a_afficher, 1):
            print(f"{i}. {role}")
    else:   
        print("Erreur : Vous n'avez pas les permissions pour créer un utilisateur.")
        return

    # Choix du rôle
    choix_role = input("\nChoisissez un rôle (numéro) : ").strip() 
    try:
        index_role = int(choix_role) - 1
        if est_superadmin(user_connecte) and 0 <= index_role < 2 : # Super Admins peuvent choisir tous les rôles sauf Super Admin (Valeur 1 et 2 en input | 0 et 1 en index)
            role = ROLES_DISPONIBLES[index_role]
        elif est_admin(user_connecte) and index_role == 0: # Admins ne peuvent choisir que "Utilisateur" (Valeur 1 en input et 0 en index)
            role = ROLES_DISPONIBLES[0] 
        elif index_role < 0 or (not est_entier(choix_role)): # Si le choix est négatif ou pas un entier, renvoie une erreur
            print("Erreur : Numéro de rôle invalide.")
            return
        else:  
            print("Erreur : Vous n'avez pas les permissions pour attribuer ce rôle.")
            return
    except ValueError:
        print("Erreur : Veuillez entrer un numéro valide.")
        return
    
    # Listing des villes
    print("\nVilles disponibles :")
    for i, ville in enumerate(VILLES_DISPONIBLES, 1):
        print(f"{i}. {ville}")
    
    # Choix de la ville
    choix_ville = input("\nChoisissez une ville (numéro) : ").strip()
    try:
        index_ville = int(choix_ville) - 1
        if 0 <= index_ville < len(VILLES_DISPONIBLES):
            ville = VILLES_DISPONIBLES[index_ville]
        else:
            print("Erreur : Numéro de ville invalide.")
            return
    except ValueError:
        print("Erreur : Veuillez entrer un numéro valide.")
        return

    # Créer l'objet User
    user = User(nom, prenom, ville, role)
    
    # Vérifier si le login existe déjà
    user_existe = db.rechercher_par_login(user.Login)
    if user_existe:
        print(f"Erreur : Un utilisateur avec le login '{user.Login}' existe déjà.")
        return
    
    # Générer le login
    user.generer_login()
    
    # Générer et hacher le mot de passe
    mot_de_passe_clair = user.generer_mot_de_passe()
    user.hacher_mot_de_passe(mot_de_passe_clair)
    
    # Ajouter à la base de données
    if db.ajouter_utilisateur(user):
        print("\n✓ Utilisateur créé avec succès !")
        print(f"Login : {user.Login}")
        print(f"Rôle : {user.Role}")
        print(f"Mot de passe temporaire : {mot_de_passe_clair}")
        print("\n⚠ IMPORTANT : Notez ce mot de passe, il ne sera plus affiché.")


def consulter_profil(user_connecte):
    """Affiche le profil de l'utilisateur connecté"""
    print("\n=== MON PROFIL ===")
    user_connecte.Afficher_User()   


def consulter_liste_utilisateurs(db):
    """Affiche la liste de tous les utilisateurs (accessible à tous)"""
    print("\n=== LISTE DES UTILISATEURS ===")
    
    liste_users = db.lister_tous_utilisateurs()
    
    if not liste_users:
        print("Aucun utilisateur enregistré.")
        return
    
    print(f"\nNombre total d'utilisateurs : {len(liste_users)}\n")
    print("-" * 80)
    print(f"{'Login':<15} | {'Nom complet':<25} | {'Rôle':<20}")
    print("-" * 80)
    
    for user in liste_users:
        nom_complet = f"{user.Prenom} {user.Nom}"
        print(f"{user.Login:<15} | {nom_complet:<25} | {user.Role:<20}")
    
    print("-" * 80)


def recherche_generale(db, recherche):
    """
    Recherche des utilisateurs dans TOUTES les colonnes textuelles de la table 'utilisateurs'.
    Colonnes prises en compte : login, nom, prenom, ville, role.
    Retourne une liste d'objets User.
    """
    connexion = db.get_connexion()
    curseur = connexion.cursor()

    pattern = f"%{recherche}%"

    curseur.execute("""
        SELECT login, nom, prenom, ville, role, password_expiry
        FROM utilisateurs
        WHERE login  LIKE ?
            OR nom    LIKE ?
            OR prenom LIKE ?
            OR ville  LIKE ?
            OR role   LIKE ?
    """, (pattern, pattern, pattern, pattern, pattern))

    resultats = curseur.fetchall()
    connexion.close()

    utilisateurs = []
    for resultat in resultats:
        user = User(
            nom=resultat[1],
            prenom=resultat[2],
            ville=resultat[3],
            role=resultat[4],
            login=resultat[0],
            password_expiry=resultat[5],
        )
        utilisateurs.append(user)

    return utilisateurs

def rechercher_utilisateur(db):
    """Recherche et affiche un ou plusieurs utilisateurs (accessible à tous)"""
    print("\n=== RECHERCHE D'UN UTILISATEUR ===")
    print("(Recherche sur login, nom, prénom, ville ou rôle)")

    recherche = input("Entrez votre recherche : ").strip()

    if not recherche:
        print("\nErreur : La recherche ne peut pas être vide.")
        return

    utilisateurs_trouves = recherche_generale(db, recherche) # Utilisation de la nouvelle fonction de recherche générale

    if not utilisateurs_trouves:
        print(f"\nErreur : Aucun utilisateur trouvé correspondant à '{recherche}'.") 
        return
    
    print(f"\n {len(utilisateurs_trouves)} utilisateur(s) trouvé(s) pour '{recherche}':") # Affichage du nombre de résultats trouvés
    
    if len(utilisateurs_trouves) == 1:
        utilisateurs_trouves[0].Afficher_User()  # Afficher les détails complets si un seul utilisateur trouvé
        return
    
    print(f"\n{'Login':<12} {'Nom':<12} {'Prénom':<12} {'Ville':<12} {'Rôle'}") # En-têtes des colonnes
    print("-" * 65)
    
    for user in utilisateurs_trouves:
        print(f"{user.Login:<12} {user.Nom:<12} {user.Prenom:<12} {user.Ville:<12} {user.Role}") # Lignes utilisateurs


def modifier_utilisateur(db, user_connecte):
    """Modifie un utilisateur existant (réservé aux admins)"""
    print("\n=== MODIFICATION D'UN UTILISATEUR ===")
    
    login = input("Entrez le login de l'utilisateur à modifier : ").strip()
    
    user = db.rechercher_par_login(login)
    
    if not user:
        print(f"\nErreur : Utilisateur '{login}' non trouvé.")
        return
    
    print(f"\nUtilisateur trouvé : {user.Prenom} {user.Nom}")
    print("\nQue souhaitez-vous modifier ?")
    print("1. Nom")
    print("2. Prénom")
    print("3. Rôle")
    print("4. Réinitialiser le mot de passe")
    print("5. Annuler")
    
    choix = input("\nVotre choix : ").strip()
    
    match choix:
            case "1":
                nouveau_nom = input("Nouveau nom : ").strip()
                if nouveau_nom:
                    user.set_nom(nouveau_nom)
                    if db.modifier_utilisateur(login, nouveau_nom=nouveau_nom):
                        print("✓ Nom modifié avec succès dans la base de données.")
    
            case "2":
                nouveau_prenom = input("Nouveau prénom : ").strip()
                if nouveau_prenom:
                    user.set_prenom(nouveau_prenom)
                    if db.modifier_utilisateur(login, nouveau_prenom=nouveau_prenom):
                        print("✓ Prénom modifié avec succès dans la base de données.")
            
            case "3":
                print("\nRôles disponibles :")
                if est_superadmin(user_connecte):
                    roles_a_afficher = ROLES_DISPONIBLES[:2]  # Super Admins auront tous les rôles d'affichés, sauf Super Admin
                    for i, role in enumerate(roles_a_afficher, 1):
                        print(f"{i}. {role}")
                elif est_admin(user_connecte):
                    roles_a_afficher = ROLES_DISPONIBLES[:1]  # Admins auront seulement "Utilisateur" d'affiché
                    for i, role in enumerate(roles_a_afficher, 1):
                        print(f"{i}. {role}")
                else:   
                    print("Erreur : Vous n'avez pas les permissions pour modifier le rôle de l'utilisateur.")
                    return
        
                choix_role = input("\nChoisissez un rôle (numéro) : ").strip()
                try:
                    index_role = int(choix_role) - 1
                    if est_superadmin(user_connecte) and 0 <= index_role < 2 : # Super Admins peuvent choisir tous les rôles sauf Super Admin (Valeur 1 et 2 en input | 0 et 1 en index)
                        role = ROLES_DISPONIBLES[index_role]
                    elif est_admin(user_connecte) and index_role == 0: # Admins ne peuvent choisir que "Utilisateur" (Valeur 1 en input et 0 en index)
                        role = ROLES_DISPONIBLES[0] 
                    elif index_role < 0 or (not est_entier(choix_role)): # Si le choix est négatif ou pas un entier, renvoie une erreur
                        print("Erreur : Numéro de rôle invalide.")
                        return
                    else:  
                        print("Erreur : Vous n'avez pas les permissions pour attribuer ce rôle.")
                        return                
                except ValueError:
                    print("Erreur : Veuillez entrer un numéro valide.")
                    return
                    
            case "4":
                nouveau_pwd = user.generer_mot_de_passe()
                user.hacher_mot_de_passe(nouveau_pwd)
                nouvelle_date_expiration = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d') # Définir une nouvelle date d'expiration dans 90 jours à partir de la date de génération


                if db.modifier_utilisateur(login, nouveau_hash=user.Password_Hash, nouvelle_date_expiration=nouvelle_date_expiration):
                    print(f"✓ Mot de passe réinitialisé avec succès.")
                    print(f"Nouveau mot de passe : {nouveau_pwd}")
                    print("⚠ IMPORTANT : Communiquez ce mot de passe à l'utilisateur.")
            
            case "5":
                print("Modification annulée.")
            
            case _:
                print("Erreur : Choix invalide.")


def supprimer_utilisateur(db, user_connecte):
    """Supprime un utilisateur (réservé aux admins)"""
    print("\n=== SUPPRESSION D'UN UTILISATEUR ===")
    
    login = input("Entrez le login de l'utilisateur à supprimer : ").strip()
    
    user = db.rechercher_par_login(login)
    
    if not user:
        print(f"\nErreur : Utilisateur '{login}' non trouvé.")
        return
    
    # Confirmation
    print(f"\nUtilisateur : {user.Prenom} {user.Nom} ({user.Role})")
    confirmation = input("Êtes-vous sûr de vouloir supprimer cet utilisateur ? (oui/non) : ").strip().lower()
    
    if confirmation == "oui":
        if user_connecte.Login == login:
            print("\nErreur : Vous ne pouvez pas supprimer votre propre compte.")
            return
        if not est_superadmin(user_connecte) and user.Role != "User":
            print("\nErreur : Vous n'avez pas les permissions pour supprimer cet utilisateur.")
            return
        if db.supprimer_utilisateur(login):
            print(f"\n✓ Utilisateur '{login}' supprimé avec succès.")
        else:
            print(f"\nErreur lors de la suppression.")
    else:
        print("\nSuppression annulée.")


def changer_mon_mot_de_passe(db, user_connecte):
    """Permet à l'utilisateur connecté de changer son propre mot de passe (accessible à tous)"""
    print("\n=== CHANGEMENT DE MOT DE PASSE ===")
    print(f"Utilisateur connecté : {user_connecte.Login}")
    
    # Demander l'ancien mot de passe
    ancien_pwd = input("\nAncien mot de passe : ")
    
    # Demander le nouveau mot de passe
    nouveau_pwd = input("Nouveau mot de passe (min. 4 caractères) : ")
    
    if ancien_pwd == nouveau_pwd:
        print("\nErreur : Le nouveau mot de passe doit être différent de l'ancien.")
        return False
    
    if len(nouveau_pwd) < 4:
        print("\nErreur : Le mot de passe doit contenir au moins 4 caractères.")
        return False
    
    # Confirmer le nouveau mot de passe
    confirmation_pwd = input("Confirmez le nouveau mot de passe : ")
    
    if nouveau_pwd != confirmation_pwd:
        print("\nErreur : Les mots de passe ne correspondent pas.")
        return False
    
    # Tenter de changer le mot de passe
    if user_connecte.changer_mot_de_passe(ancien_pwd, nouveau_pwd):
        # Mettre à jour dans la base de données
        if db.modifier_utilisateur(user_connecte.Login, nouveau_hash=user_connecte.Password_Hash):
            print("\n✓ Votre mot de passe a été changé avec succès !")
            return True
        else:
            print("\nErreur lors de la sauvegarde du nouveau mot de passe.")
            return False
    else:
        print("\nErreur : Ancien mot de passe incorrect.")
        return False



def authentifier_utilisateur(db):
    """Authentifie un utilisateur """
    print("\n=== AUTHENTIFICATION ===")
    
    login_valid = False
    while not login_valid:
        login = input("Login : ").strip()

        user = db.rechercher_par_login(login)
        if not user:
            print("Login incorrect. Veuillez réessayer.")
            continue

        if not db.verifier_bloquage_utilisateur(login):
            print("Compte bloqué. Merci de réessayer plus tard")
            continue

        else:
            login_valid = True

    tentatives = 3
    while tentatives > 0:
        if tentatives < 3:
            print(f"\n⚠ Il vous reste {tentatives} tentative(s)")
        mot_de_passe = input("Mot de passe : ")
        
        # Vérifier le mot de passe
        if user.verifier_mot_de_passe(mot_de_passe):
            print(f"\nAuthentification réussie. Bienvenue {user.Prenom} {user.Nom} !")
            return user
        else:
            tentatives -= 1
            if tentatives > 0:
                print("Login ou mot de passe incorrect. Veuillez réessayer.")

    db.bloquer_utilisateur(login)

    print("\n" + "=" * 60)
    print(f"ACCÈS REFUSÉ - Nombre maximum de tentatives atteint. Le compte {user.Login} a été bloqué.")
    print("=" * 60)
    quit()