from classes import User

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
    return user.Role == "Super Admin" or "Admin"

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
        if est_superadmin(user_connecte) and 0 <= index_role < len(ROLES_DISPONIBLES)-1: # Super Admins peuvent choisir tous les rôles sauf Super Admin (Valeur 1 et 2 en input | 0 et 1 en index)
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


def rechercher_utilisateur(db):
    """Recherche et affiche un utilisateur (accessible à tous)"""
    print("\n=== RECHERCHE D'UN UTILISATEUR ===")
    
    login = input("Entrez le login à rechercher : ").strip()
    
    user = db.rechercher_par_login(login)
    
    if user:
        print("\n✓ Utilisateur trouvé :")
        user.Afficher_User()
    else:
        print(f"\n✗ Aucun utilisateur trouvé avec le login '{login}'.")


def modifier_utilisateur(db):
    """Modifie un utilisateur existant (réservé aux admins)"""
    print("\n=== MODIFICATION D'UN UTILISATEUR ===")
    
    login = input("Entrez le login de l'utilisateur à modifier : ").strip()
    
    user = db.rechercher_par_login(login)
    
    if not user:
        print(f"\n✗ Utilisateur '{login}' non trouvé.")
        return
    
    print(f"\nUtilisateur trouvé : {user.Prenom} {user.Nom}")
    print("\nQue souhaitez-vous modifier ?")
    print("1. Nom")
    print("2. Prénom")
    print("3. Rôle")
    print("4. Réinitialiser le mot de passe")
    print("5. Annuler")
    
    choix = input("\nVotre choix : ").strip()
    
    if choix == "1":
        nouveau_nom = input("Nouveau nom : ").strip()
        if nouveau_nom:
            user.set_nom(nouveau_nom)
            if db.modifier_utilisateur(login, nouveau_nom=nouveau_nom):
                print("✓ Nom modifié avec succès dans la base de données.")
    
    elif choix == "2":
        nouveau_prenom = input("Nouveau prénom : ").strip()
        if nouveau_prenom:
            user.set_prenom(nouveau_prenom)
            if db.modifier_utilisateur(login, nouveau_prenom=nouveau_prenom):
                print("✓ Prénom modifié avec succès dans la base de données.")
    
    elif choix == "3":
        print("\nRôles disponibles :")
        for i, role in enumerate(ROLES_DISPONIBLES, 1):
            print(f"{i}. {role}")
        
        choix_role = input("\nChoisissez un rôle (numéro) : ").strip()
        try:
            index_role = int(choix_role) - 1
            if 0 <= index_role < len(ROLES_DISPONIBLES):
                nouveau_role = ROLES_DISPONIBLES[index_role]
                user.set_role(nouveau_role)
                if db.modifier_utilisateur(login, nouveau_role=nouveau_role):
                    print("✓ Rôle modifié avec succès dans la base de données.")
        except ValueError:
            print("✗ Veuillez entrer un numéro valide.")
    
    elif choix == "4":
        nouveau_pwd = user.generer_mot_de_passe()
        user.hacher_mot_de_passe(nouveau_pwd)
        
        if db.modifier_utilisateur(login, nouveau_hash=user.Password_Hash):
            print(f"✓ Mot de passe réinitialisé avec succès.")
            print(f"Nouveau mot de passe : {nouveau_pwd}")
            print("⚠ IMPORTANT : Communiquez ce mot de passe à l'utilisateur.")
    
    elif choix == "5":
        print("Modification annulée.")
    
    else:
        print("✗ Choix invalide.")


def supprimer_utilisateur(db):
    """Supprime un utilisateur (réservé aux admins)"""
    print("\n=== SUPPRESSION D'UN UTILISATEUR ===")
    
    login = input("Entrez le login de l'utilisateur à supprimer : ").strip()
    
    user = db.rechercher_par_login(login)
    
    if not user:
        print(f"\n✗ Utilisateur '{login}' non trouvé.")
        return
    
    # Confirmation
    print(f"\nUtilisateur : {user.Prenom} {user.Nom} ({user.Role})")
    confirmation = input("Êtes-vous sûr de vouloir supprimer cet utilisateur ? (oui/non) : ").strip().lower()
    
    if confirmation == "oui":
        if db.supprimer_utilisateur(login):
            print(f"\n✓ Utilisateur '{login}' supprimé avec succès.")
        else:
            print(f"\n✗ Erreur lors de la suppression.")
    else:
        print("\nSuppression annulée.")


def changer_mon_mot_de_passe(db, user_connecte):
    """Permet à l'utilisateur connecté de changer son propre mot de passe (accessible à tous)"""
    print("\n=== CHANGEMENT DE MOT DE PASSE ===")
    print(f"Utilisateur connecté : {user_connecte.Login}")
    
    # Demander l'ancien mot de passe
    ancien_pwd = input("\nAncien mot de passe : ").strip()
    
    # Demander le nouveau mot de passe
    nouveau_pwd = input("Nouveau mot de passe (min. 4 caractères) : ").strip()
    
    if len(nouveau_pwd) < 4:
        print("\n✗ Le mot de passe doit contenir au moins 4 caractères.")
        return False
    
    # Confirmer le nouveau mot de passe
    confirmation_pwd = input("Confirmez le nouveau mot de passe : ").strip()
    
    if nouveau_pwd != confirmation_pwd:
        print("\n✗ Les mots de passe ne correspondent pas.")
        return False
    
    # Tenter de changer le mot de passe
    if user_connecte.changer_mot_de_passe(ancien_pwd, nouveau_pwd):
        # Mettre à jour dans la base de données
        if db.modifier_utilisateur(user_connecte.Login, nouveau_hash=user_connecte.Password_Hash):
            print("\n✓ Votre mot de passe a été changé avec succès !")
            return True
        else:
            print("\n✗ Erreur lors de la sauvegarde du nouveau mot de passe.")
            return False
    else:
        print("\n✗ Ancien mot de passe incorrect.")
        return False


def authentifier_utilisateur(db):
    """Authentifie un utilisateur """
    print("\n=== AUTHENTIFICATION ===")
    
    login = input("Login : ").strip()
    mot_de_passe = input("Mot de passe : ").strip()
    
    user = db.rechercher_par_login(login)
    
    if not user:
        print("\nLogin ou mot de passe incorrect.")
        return None
    
    # Vérifier le mot de passe
    if user.verifier_mot_de_passe(mot_de_passe):
        print(f"\nAuthentification réussie. Bienvenue {user.Prenom} {user.Nom} !")
        return user
    else:
        print("\nLogin ou mot de passe incorrect.")
        return None