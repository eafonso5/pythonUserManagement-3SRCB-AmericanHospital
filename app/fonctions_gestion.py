from classes import User
from datetime import datetime, timedelta

# Définition des rôles disponibles dans le système
ROLES_DISPONIBLES = [
    "User",
    "Admin",
    "Super Admin"
]

# Liste des villes disponibles pour l’utilisateur
VILLES_DISPONIBLES = [
    "Paris",
    "Marseille",
    "Rennes",
    "Grenoble"
]


def est_entier(valeur):
    """Vérifie si une chaîne peut être convertie en entier."""
    try:
        int(valeur)
        return True
    except ValueError:
        return False
    

def est_superadmin(user):
    """Retourne True si l'utilisateur possède le rôle 'Super Admin'."""
    return user.Role == "Super Admin"


def est_admin(user):
    """Retourne True si l'utilisateur est Admin ou Super Admin."""
    return user.Role == "Super Admin" or user.Role == "Admin"


def creer_utilisateur(db, user_connecte):
    """Crée un nouvel utilisateur. Fonction réservée aux administrateurs."""

    print("\n=== CRÉATION D'UN NOUVEL UTILISATEUR ===")
    
    # Demande du nom de famille
    nom = input("Nom : ").strip()
    if not nom:
        print("Erreur : Le nom ne peut pas être vide.")
        return
    
    # Demande du prénom
    prenom = input("Prénom : ").strip()
    if not prenom:
        print("Erreur : Le prénom ne peut pas être vide.")
        return
    
    # Vérification qu'un utilisateur avec le même nom+prénom n'existe pas déjà
    user_deja_present = db.rechercher_par_nom_prenom(nom, prenom)
    if user_deja_present:
        print(f"Erreur : Un utilisateur avec le nom '{nom}' et le prénom '{prenom}' existe déjà ")
        print(f"(Login de l'utilisateur : {user_deja_present.Login}).")
        return
    
    # Détermination des rôles pouvant être attribués selon le rôle du créateur
    if est_superadmin(user_connecte):
        # Un Super Admin peut créer User + Admin
        roles_attribuables = ROLES_DISPONIBLES[:2]
    elif est_admin(user_connecte):
        # Un Admin ne peut créer que des Users
        roles_attribuables = ROLES_DISPONIBLES[:1]
    else:
        # Vérification de sécurité supplémentaire
        print("Erreur : Vous n'avez pas les permissions pour créer un utilisateur.")
        return

    # Si un seul rôle possible, attribution automatique
    if len(roles_attribuables) == 1:
        role = roles_attribuables[0]
        print(f"\nRôle automatiquement attribué : {role}")
    
    # Sinon, affichage et choix manuel du rôle
    else:
        print("\nRôles disponibles :")
        for i, r in enumerate(roles_attribuables, 1):
            print(f"{i}. {r}")

        # Boucle pour sécuriser la saisie du rôle
        while True:
            choix_role = input("\nChoisissez un rôle (numéro) : ").strip()

            if not est_entier(choix_role):
                print("Erreur : Veuillez entrer un numéro valide.")
                continue

            index_role = int(choix_role) - 1

            # Vérification de l’index sélectionné
            if 0 <= index_role < len(roles_attribuables):
                role = roles_attribuables[index_role]
                break
            else:
                print("Erreur : Numéro de rôle invalide.")

    # Récupération de la liste des villes selon le rôle
    if est_superadmin(user_connecte):
        villes_a_afficher = VILLES_DISPONIBLES
    elif est_admin(user_connecte):
        villes_a_afficher = [user_connecte.Ville]

    # Les villes attribuables sont les mêmes que celles affichées
    villes_attribuables = villes_a_afficher

    # Si une seule ville possible, attribution automatique
    if len(villes_attribuables) == 1:
        ville = villes_attribuables[0]
        print(f"\nVille automatiquement attribuée : {ville}")

    # Sinon, choix manuel de la ville
    else:
        # Affichage numéroté des villes
        for i, ville in enumerate(villes_a_afficher, start=1):
            print(f"{i}. {ville}")   
        choix_ville = input("\nChoisissez une ville (numéro) : ").strip()
        try:
            index_ville = int(choix_ville) - 1

            # Vérification de la validité de l’indice
            if 0 <= index_ville < len(VILLES_DISPONIBLES):
                ville = VILLES_DISPONIBLES[index_ville]
            else:
                print("Erreur : Numéro de ville invalide.")
                return
        except ValueError:
            print("Erreur : Veuillez entrer un numéro valide.")
            return

    # CONTROLE : Un seul Admin/Super Admin par ville
    if role in ("Admin", "Super Admin"):
        existe = db.existe_admin_ou_superadmin_dans_ville(ville)
        if existe:
            print(f"\nERREUR : La ville '{ville}' possède déjà un {existe['role']} ({existe['login']}).")
            print("Impossible de créer un second Admin/Super Admin pour cette ville.")
            return

    # Création de l’objet User
    user = User(nom, prenom, ville, role)
    
    # Génération du login initial
    user.generer_login()
    login_de_base = user.Login
    
    # Vérification que le login n'existe pas déjà
    nouveau_login = login_de_base
    suffixe = 1

    # Incrémentation automatique en cas de doublon de login
    while db.rechercher_par_login(nouveau_login) is not None:
        nouveau_login = f"{login_de_base}{suffixe}"
        suffixe += 1
    
    user.Login = nouveau_login 
    
    # Génération d'un mot de passe temporaire
    mot_de_passe_clair = user.generer_mot_de_passe()

    # Hachage du mot de passe généré
    user.hacher_mot_de_passe(mot_de_passe_clair)
    
    # Sauvegarde du nouvel utilisateur en base
    if db.ajouter_utilisateur(user):
        print("\n✓ Utilisateur créé avec succès !")
        print(f"Login : {user.Login}")
        print(f"Rôle : {user.Role}")
        print(f"Mot de passe temporaire : {mot_de_passe_clair}")
        print("\n⚠ IMPORTANT : Notez ce mot de passe, il ne sera plus affiché.")


def consulter_profil(user_connecte):
    """Affiche les informations du compte de l’utilisateur connecté."""
    print("\n=== MON PROFIL ===")
    user_connecte.Afficher_User()


def consulter_liste_utilisateurs(db, user_connecte):
    """Affiche la liste des utilisateurs, avec filtrage avancé pour le Super Admin."""

    print("\n=== LISTE DES UTILISATEURS ===")

    # Le Super Admin peut choisir d'afficher toutes les villes ou une ville spécifique
    if est_superadmin(user_connecte):

        print("\nOptions d'affichage :")
        print("1. Afficher TOUTES les villes")
        print("2. Filtrer par une ville spécifique")
        
        choix = input("Votre choix : ").strip()

        # Option 1 : toutes les villes
        if choix == "1":
            liste_users = db.lister_tous_utilisateurs()
        
        # Option 2 : filtrer par ville 
        elif choix == "2":
            print("\nVilles disponibles :")
            for i, ville in enumerate(VILLES_DISPONIBLES, start=1):
                print(f"{i}. {ville}")

            choix_ville = input("\nChoisissez une ville (numéro) : ").strip()

            try:
                index = int(choix_ville) - 1

                if 0 <= index < len(VILLES_DISPONIBLES):
                    ville_cible = VILLES_DISPONIBLES[index]
                    liste_users = db.lister_tous_utilisateurs(ville_visible=ville_cible)
                else:
                    print("Erreur : numéro de ville invalide.")
                    return

            except ValueError:
                print("Erreur : veuillez entrer un numéro valide.")
                return
        
        # Choix invalide
        else:
            print("Erreur : choix invalide.")
            return
    
    # l'admin classique ne peut voir que sa propre ville
    else:
        liste_users = db.lister_tous_utilisateurs(ville_filter=user_connecte.Ville)

    # Vérification des résultats
    if not liste_users:
        print("\nAucun utilisateur trouvé pour ce filtre.")
        return
    
    print(f"\nNombre total d'utilisateurs : {len(liste_users)}\n")
    print("-" * 80)
    print(f"{'Login':<15} | {'Nom complet':<25} | {'Rôle':<15} | {'Ville':<15}")
    print("-" * 80)
    
    # Affichage formaté
    for user in liste_users:
        nom_complet = f"{user.Prenom} {user.Nom}"
        print(f"{user.Login:<15} | {nom_complet:<25} | {user.Role:<15} | {user.Ville:<15}")
    
    print("-" * 80)

def recherche_generale(db, recherche, user_connecte):
    """
    Effectue une recherche dans plusieurs colonnes :
    login, nom, prénom, ville, rôle.
    Retourne une liste d’objets User correspondants.
    """

    connexion = db.get_connexion()
    curseur = connexion.cursor()

    pattern = f"%{recherche}%"

    # Super Admin : pas de filtrage sur la ville
    if est_superadmin(user_connecte):
        curseur.execute("""
            SELECT login, nom, prenom, ville, role, password_expiry
            FROM utilisateurs
            WHERE login  LIKE ?
               OR nom    LIKE ?
               OR prenom LIKE ?
               OR ville  LIKE ?
               OR role   LIKE ?
        """, (pattern, pattern, pattern, pattern, pattern))

    # Admin : filtrage sur sa ville
    else:
        curseur.execute("""
            SELECT login, nom, prenom, ville, role, password_expiry
            FROM utilisateurs
            WHERE (login  LIKE ?
               OR nom    LIKE ?
               OR prenom LIKE ?
               OR ville  LIKE ?
               OR role   LIKE ?)
              AND ville = ?
        """, (pattern, pattern, pattern, pattern, pattern, user_connecte.Ville))
        
    resultats = curseur.fetchall()
    connexion.close()

    utilisateurs = []

    # Reconstruction d’un User pour chaque ligne trouvée
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


def rechercher_utilisateur(db, user_connecte):
    """Recherche un ou plusieurs utilisateurs selon une valeur textuelle saisie."""

    print("\n=== RECHERCHE D'UN UTILISATEUR ===")
    print("(Recherche sur login, nom, prénom, ville ou rôle)")

    recherche = input("Entrez votre recherche : ").strip()

    if not recherche:
        print("\nErreur : La recherche ne peut pas être vide.")
        return

    # Appel de la recherche globale
    
    utilisateurs_trouves = recherche_generale(db, recherche, user_connecte)

    # Gestion d’absence de résultat
    if not utilisateurs_trouves:
        print(f"\nErreur : Aucun utilisateur trouvé correspondant à '{recherche}'.")
        return
    
    print(f"\n {len(utilisateurs_trouves)} utilisateur(s) trouvé(s) pour '{recherche}':")
    
    # Si un seul utilisateur, on affiche sa fiche complète
    if len(utilisateurs_trouves) == 1:
        utilisateurs_trouves[0].Afficher_User()
        return
    
    # Sinon, tableau récapitulatif
    print(f"\n{'Login':<12} {'Nom':<12} {'Prénom':<12} {'Ville':<12} {'Rôle'}")
    print("-" * 65)
    
    for user in utilisateurs_trouves:
        print(f"{user.Login:<12} {user.Nom:<12} {user.Prenom:<12} {user.Ville:<12} {user.Role}")


def modifier_utilisateur(db, user_connecte):
    """Permet de modifier un utilisateur existant (fonction réservée aux admins)."""

    print("\n=== MODIFICATION D'UN UTILISATEUR ===")
    
    # Saisie du login de l’utilisateur ciblé
    login = input("Entrez le login de l'utilisateur à modifier : ").strip()
    
    user = db.rechercher_par_login(login)
    
    # Aucun utilisateur avec ce login
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
            # Modification du nom
            nouveau_nom = input("Nouveau nom : ").strip()
            if nouveau_nom:
                user.set_nom(nouveau_nom)
                db.modifier_utilisateur(login, nouveau_nom=nouveau_nom)

        case "2":
            # Modification du prénom
            nouveau_prenom = input("Nouveau prénom : ").strip()
            if nouveau_prenom:
                user.set_prenom(nouveau_prenom)
                db.modifier_utilisateur(login, nouveau_prenom=nouveau_prenom)

        case "3":
            # Modification du rôle, avec contrôle des permissions
            print("\nRôles disponibles :")
            
            if est_superadmin(user_connecte):
                roles_a_afficher = ROLES_DISPONIBLES[:2]
            elif est_admin(user_connecte):
                roles_a_afficher = ROLES_DISPONIBLES[:1]
            else:
                print("Erreur : Vous n'avez pas les permissions pour modifier le rôle.")
                return
            
            for i, role in enumerate(roles_a_afficher, 1):
                print(f"{i}. {role}")
            
            choix_role = input("\nChoisissez un rôle (numéro) : ").strip()

            try:
                index_role = int(choix_role) - 1

                if est_superadmin(user_connecte) and 0 <= index_role < 2:
                    role = ROLES_DISPONIBLES[index_role]

                elif est_admin(user_connecte) and index_role == 0:
                    role = ROLES_DISPONIBLES[0]

                elif index_role < 0 or (not est_entier(choix_role)):
                    print("Erreur : Numéro de rôle invalide.")
                    return
                
                else:
                    print("Erreur : Vous n'avez pas les permissions pour attribuer ce rôle.")
                    return

                db.modifier_utilisateur(login, nouveau_role=role)

            except ValueError:
                print("Erreur : Veuillez entrer un numéro valide.")
                return
            
        case "4":
            # Réinitialisation du mot de passe
            nouveau_pwd = user.generer_mot_de_passe()
            user.hacher_mot_de_passe(nouveau_pwd)
            
            nouvelle_date_expiration = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

            if db.modifier_utilisateur(login, nouveau_hash=user.Password_Hash,
                                       nouvelle_expiration=nouvelle_date_expiration):
                print("✓ Mot de passe réinitialisé.")
                print(f"Nouveau mot de passe : {nouveau_pwd}")

        case "5":
            # Annulation de la modification
            print("Modification annulée.")
        
        case _:
            print("Erreur : Choix invalide.")


def supprimer_utilisateur(db, user_connecte):
    """Supprime un utilisateur si les permissions le permettent."""

    print("\n=== SUPPRESSION D'UN UTILISATEUR ===")
    
    login = input("Entrez le login de l'utilisateur à supprimer : ").strip()
    
    user = db.rechercher_par_login(login)

    # Vérification de l'existence
    if not user:
        print(f"\nErreur : Utilisateur '{login}' non trouvé.")
        return
    
    print(f"\nUtilisateur : {user.Prenom} {user.Nom} ({user.Role})")
    confirmation = input("Êtes-vous sûr de vouloir supprimer cet utilisateur ? (oui/non) : ").strip().lower()
    
    if confirmation == "oui":

        # Sécurité : un utilisateur ne peut se supprimer lui-même
        if user_connecte.Login == login:
            print("\nErreur : Vous ne pouvez pas supprimer votre propre compte.")
            return
        
        # Un Admin ne peut supprimer qu’un User (pas un Admin ni Super Admin)
        if not est_superadmin(user_connecte) and user.Role != "User":
            print("\nErreur : Vous n'avez pas les permissions pour supprimer cet utilisateur.")
            return
        
        # Exécution de la suppression
        db.supprimer_utilisateur(login)
        print(f"\n✓ Utilisateur '{login}' supprimé avec succès.")
    
    else:
        print("\nSuppression annulée.")


def changer_mon_mot_de_passe(db, user_connecte):
    """Permet à un utilisateur de modifier son propre mot de passe."""

    print("\n=== CHANGEMENT DE MOT DE PASSE ===")
    print(f"Utilisateur connecté : {user_connecte.Login}")
    
    # Nombre d'essais autorisés
    tentatives = 3

    while tentatives > 0:

        # Ancien mot de passe
        ancien_pwd = input("\nAncien mot de passe : ")
        
        # Nouveau mot de passe
        nouveau_pwd = input("Nouveau mot de passe (min. 4 caractères) : ")
        
        # Vérification basique de cohérence
        if ancien_pwd == nouveau_pwd:
            print("\nErreur : Le nouveau mot de passe doit être différent de l'ancien.")
            tentatives -= 1
            continue
        
        if len(nouveau_pwd) < 4:
            print("\nErreur : Le mot de passe doit contenir au moins 4 caractères.")
            tentatives -= 1
            continue
        
        # Confirmation du mot de passe
        confirmation_pwd = input("Confirmez le nouveau mot de passe : ")
        
        if nouveau_pwd != confirmation_pwd:
            print("\nErreur : Les mots de passe ne correspondent pas.")
            tentatives -= 1
            continue
        
        # Tentative de modification
        if user_connecte.changer_mot_de_passe(ancien_pwd, nouveau_pwd):
            
            # Mise à jour en base via le hash modifié
            if db.modifier_utilisateur(user_connecte.Login, nouveau_hash=user_connecte.Password_Hash):
                print("\n✓ Votre mot de passe a été changé avec succès !")
                return True
            
            else:
                print("\nErreur lors de la sauvegarde du nouveau mot de passe.")
                return False
        
        # Si ancien mot de passe incorrect
        else:
            print("\nErreur : Ancien mot de passe incorrect.")
            tentatives -= 1
            continue

    # Si les 3 tentatives sont épuisées
    print("\nNombre maximum de tentatives atteint. Retour au menu.")


def authentifier_utilisateur(db):
    """Authentifie un utilisateur à l'aide de son login et de son mot de passe."""

    print("\n=== AUTHENTIFICATION ===")
    
    login_valid = False

    # Boucle de vérification du login
    while not login_valid:
        login = input("Login : ").strip()

        # Recherche du compte en base
        user = db.rechercher_par_login(login)

        if not user:
            print("Login incorrect. Veuillez réessayer.")
            continue

        # Vérification du blocage du compte
        if not db.verifier_bloquage_utilisateur(login):
            print("Compte bloqué. Merci de réessayer plus tard")
            continue

        # Si tout est bon, on peut passer au mot de passe
        login_valid = True

    # Trois tentatives pour le mot de passe
    tentatives = 3
    while tentatives > 0:

        if tentatives < 3:
            print(f"\n⚠ Il vous reste {tentatives} tentative(s)")
        
        mot_de_passe = input("Mot de passe : ")
        
        # Vérification du mot de passe via le hash
        if user.verifier_mot_de_passe(mot_de_passe):
            print(f"\nAuthentification réussie. Bienvenue {user.Prenom} {user.Nom} !")
            return user
        
        # En cas d'échec
        else:
            tentatives -= 1

            if tentatives > 0:
                print("Login ou mot de passe incorrect. Veuillez réessayer.")

    # Si les trois tentatives échouent
    db.bloquer_utilisateur(login)

    print("\n" + "=" * 60)
    print(f"ACCÈS REFUSÉ - Nombre maximum de tentatives atteint. Le compte {user.Login} a été bloqué.")
    print("=" * 60)
    quit()
