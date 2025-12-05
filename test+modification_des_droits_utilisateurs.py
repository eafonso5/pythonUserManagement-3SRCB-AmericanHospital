import hashlib # Pour le hachage sécurisé du mot de passe (contrainte sécurité)
import os      # Pour générer un 'salt' (sel) aléatoire, renforçant le hachage
import secrets # Pour générer un mot de passe initial aléatoire et sécurisé

# --- Variables de stockage temporaire (en mémoire uniquement) ---
LISTE_UTILISATEURS_EN_MEMOIRE = []


### Déclaration de classe Salarié
class Salarié(object):
    """
    Classe de base pour tout employé.
    Fonctionnalités : Stockage Nom/Prénom et validation de base.
    """

### Constructeur de la classe : construite et initialiser un  objet
    def __init__(self, nom, pnom):
        print ("Création d'un objet salarié...")
        self.Nom=nom
        self.Prenom=pnom

### Les méthodes getter et setter (sécurité d'accès)
    def get_nom(self):
        return self.Nom
    def get_pnom(self):
        return self.Prenom

    def set_nom(self, nouveau_nom):   # Méthode 'set' pour modifier le nom
        if nouveau_nom.strip() == "":
            print ("Le nom de l'employé ne peut pas être vide!!!!")
        else:
            self.Nom = nouveau_nom
            print ("Le Nom à été modifié.")

    def set_pnom(self, nouveau_pnom):   # Méthode 'set' pour modifier le nom
        if nouveau_pnom.strip() == "":
            print ("Le prénom de l'employé ne peut pas être vide!!!!")
        else:
            self.Prenom = nouveau_pnom
            print ("Le Prénom à été modifié.")

### Autres méthode, exemple affichage
    def afficher(self):
        print (f"{self.Prenom} {self.Nom} a été ajouté(e) en tant que Salarié.")


#---------------------------------------------------------------------------------------------------#

class User(Salarié):
    """
    Classe dérivée de Salarié, représentant un utilisateur avec des droits d'accès.
    Intègre les contraintes de Login (génération auto) et PWD (hachage).
    """
### constructeur de la nouvelle classe User
    def __init__(self, nom, pnom, role, password_initial=None):
        print ("Création d'un objet User...")
        super().__init__(nom, pnom)

        self.Role = role
        self.Login = self._generer_login(pnom, nom)
        self.Password_Hashed = None
        self.Salt = None

        if password_initial:
            self.hacher_mot_de_passe(password_initial)

    def _generer_login(self, prenom, nom):
        """
        Implémentation de la règle de gestion de Login : première lettre du prénom + nom.
        """
        initial = prenom[0].lower()
        nom_nettoye = nom.split()[0].lower()
        return f"{initial}{nom_nettoye}"

    def hacher_mot_de_passe(self, mot_de_passe_clair):
        """Hache le mot de passe en utilisant PBKDF2 avec SHA-256 et un sel."""
        self.Salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            mot_de_passe_clair.encode('utf-8'),
            self.Salt,
            100000
        )
        self.Password_Hashed = key.hex()

    def verifier_mot_de_passe(self, mot_de_passe_clair):
        """Vérifie si le mot de passe clair correspond au hash stocké."""
        if not self.Password_Hashed or not self.Salt:
            return False

        nouveau_hash = hashlib.pbkdf2_hmac(
            'sha256',
            mot_de_passe_clair.encode('utf-8'),
            self.Salt,
            100000
        ).hex()

        return nouveau_hash == self.Password_Hashed

    def Afficher_User(self):
        """Affiche les informations critiques (sans le hash/salt)."""
        print(f"--- Fiche Utilisateur ---")
        print(f"User ID      : {self.Login}")
        print(f"Nom Complet  : {self.get_full_name()}")
        print(f"Rôle         : {self.Role}")
        print(f"Statut PWD   : Haché et Sécurisé")

    def get_full_name(self):
        """Méthode utilitaire pour obtenir le nom complet."""
        return f"{self.Prenom} {self.Nom}"


# -----------------------------------------------------------------------------
# FONCTIONS DE GESTION DES UTILISATEURS
# -----------------------------------------------------------------------------

def generer_mot_de_passe_initial():
    """Génère un mot de passe fort et aléatoire pour l'initialisation."""
    return secrets.token_urlsafe(16)

def creer_nouvel_utilisateur(nom, prenom, role):
    """Crée un utilisateur et retourne l'objet utilisateur ET le mot de passe clair initial."""
    pwd_initial = generer_mot_de_passe_initial()

    nouvel_user = User(nom, prenom, role, password_initial=pwd_initial)

    global LISTE_UTILISATEURS_EN_MEMOIRE
    LISTE_UTILISATEURS_EN_MEMOIRE.append(nouvel_user)

    print(f"\n[Création OK] Login : {nouvel_user.Login}, Rôle : {role}")
    print(f"!!! PWD initial à communiquer : {pwd_initial} (mot de passe haché en interne)")
    return nouvel_user, pwd_initial

def rechercher_utilisateur(login_cible):
    """Recherche un utilisateur par son Login."""
    for user in LISTE_UTILISATEURS_EN_MEMOIRE:
        if user.Login.lower() == login_cible.lower():
            return user
    return None

def modifier_utilisateur_complet(login_cible, nouveau_role=None, nouveau_pwd_clair=None):
    """Met à jour le rôle ou le mot de passe de l'utilisateur ciblé."""
    user = rechercher_utilisateur(login_cible)

    if user is None:
        print(f"\n[Erreur Modification] Utilisateur '{login_cible}' non trouvé.")
        return False

    print(f"\n[Modification] Modification de l'utilisateur : {user.Login}")
    modification_faite = False

    # 1. Modification du Rôle
    if nouveau_role is not None and user.Role != nouveau_role:
        user.Role = nouveau_role
        print(f"-> Rôle mis à jour : {user.Role}")
        modification_faite = True

    # 2. Modification du Mot de Passe
    if nouveau_pwd_clair is not None:
        user.hacher_mot_de_passe(nouveau_pwd_clair)
        print("-> Mot de passe mis à jour et haché avec succès.")
        modification_faite = True

    if not modification_faite:
        print("-> Aucune modification effectuée (rôle et/ou mot de passe non spécifiés/identiques).")

    return modification_faite


def supprimer_utilisateur(login_cible):
    """Supprime un utilisateur de la liste."""
    user_a_supprimer = rechercher_utilisateur(login_cible)

    if user_a_supprimer:
        global LISTE_UTILISATEURS_EN_MEMOIRE
        LISTE_UTILISATEURS_EN_MEMOIRE.remove(user_a_supprimer)
        print(f"\n[Suppression OK] L'utilisateur '{login_cible}' a été retiré du système.")
    else:
        print(f"\n[Erreur] Utilisateur '{login_cible}' non trouvé.")

def consulter_liste_utilisateurs():
    """Affiche la liste complète des utilisateurs."""
    print("\n--- CONSULTATION : LISTE DES UTILISATEURS ENREGISTRÉS ---")
    if not LISTE_UTILISATEURS_EN_MEMOIRE:
        print("La liste est vide.")
        return

    for user in LISTE_UTILISATEURS_EN_MEMOIRE:
        print(f"| {user.Login.ljust(15)} | Rôle: {user.Role.ljust(15)} | Nom: {user.get_full_name()}")
    print("---------------------------------------------------------")


# -----------------------------------------------------------------------------
# PROGRAMME PRINCIPAL (Tests des fonctionnalités)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("<<< DÉBUT DE L'OUTIL DE GESTION DES UTILISATEURS >>>")

    # 1. CRÉATION
    print("\n--- 1. Phase de Création ---")

    admin_supreme, pwd_supreme_test = creer_nouvel_utilisateur("Admin", "Super", "Super Admin")
    admin_marseille, pwd_marseille_test = creer_nouvel_utilisateur("Duval", "Marc", "Admin Regional")
    user_medical, pwd_medical_test = creer_nouvel_utilisateur("Girard", "Alice", "Médecin")

    # 2. CONSULTATION
    consult_list = consulter_liste_utilisateurs()

    # 3. RECHERCHE et AUTHENTIFICATION
    print("\n--- 3. Phase de Recherche et Authentification ---")

    login_a_tester = admin_supreme.Login
    user_trouve = rechercher_utilisateur(login_a_tester)

    if user_trouve:
        pwd_clair = pwd_supreme_test
        print(f"Test PWD : {pwd_clair} (Mot de passe clair utilisé pour la vérification)")

        if user_trouve.verifier_mot_de_passe(pwd_clair):
            print(f"[AUTH OK] Utilisateur {user_trouve.Login} authentifié avec succès.")
        else:
            print(f"[AUTH ÉCHEC] Le mot de passe haché n'a pas correspondu.")

        if not user_trouve.verifier_mot_de_passe("mauvais_mot_de_passe"):
             print(f"[AUTH OK] Tentative échouée bloquée pour {user_trouve.Login}.")

    # 4. GESTION BASIQUE (Modification Nom/Suppression)
    print("\n--- 4. Gestion Basique ---")

    user_medical.set_nom("Girard-Smith")
    user_medical.Afficher_User()

    supprimer_utilisateur(admin_marseille.Login)

    # 5. TEST DE LA MODIFICATION COMPLÈTE
    print("\n--- 5. Test de Modification Complète ---")

    new_pwd_test = "NouveauMDP!2026"

    # Test 1 : Modifier le rôle et le mot de passe de l'utilisateur 'agirard'
    modification1 = modifier_utilisateur_complet(
        login_cible="agirard",
        nouveau_role="Pharmacien",
        nouveau_pwd_clair=new_pwd_test
    )

    if modification1:
        # Vérification de l'authentification avec le nouveau mot de passe
        user_modifie = rechercher_utilisateur("agirard")
        if user_modifie.verifier_mot_de_passe(new_pwd_test):
            print(f"[AUTH OK] Vérification du nouveau PWD pour {user_modifie.Login} réussie.")
        else:
            print("[AUTH ÉCHEC] Erreur lors de la vérification du nouveau mot de passe.")

    # Test 2 : Essayer de modifier un utilisateur qui n'existe pas
    modifier_utilisateur_complet(login_cible="inexistant", nouveau_role="Visiteur")

    # CONSULTATION FINALE après toutes les opérations
    print("\n--- CONSULTATION FINALE ---")
    consult_list_end = consulter_liste_utilisateurs()

    print("\n<<< FIN DE L'EXÉCUTION DU PROTOTYPE >>>")
