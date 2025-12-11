import secrets
import hashlib

class Salarie(object):
    """Classe représentant un salarié de l'hôpital.
       Sert de base pour la classe User (héritage)."""

    def __init__(self, nom, prenom, ville):
        """Initialise les informations principales d’un salarié."""
        self.Nom = nom
        self.Prenom = prenom
        self.Ville = ville

    def get_nom(self):
        """Retourne le nom du salarié."""
        return self.Nom
    
    def get_prenom(self):
        """Retourne le prénom du salarié."""
        return self.Prenom
    
    def get_ville(self):
        """Retourne la ville du salarié."""
        return self.Ville


    def set_nom(self, nouveau_nom):
        """Modifie le nom si la nouvelle valeur est valide."""
        if nouveau_nom.strip() == "":
            print("Le nom de l'employé ne peut pas être vide !")
        else:
            self.Nom = nouveau_nom
            print("Le Nom a été modifié.")
    
    def set_prenom(self, nouveau_prenom):
        """Modifie le prénom si la nouvelle valeur est valide."""
        if nouveau_prenom.strip() == "":
            print("Le prénom de l'employé ne peut pas être vide !")
        else:
            self.Prenom = nouveau_prenom
            print("Le Prénom a été modifié.")

    def set_ville(self, nouvelle_ville):
        """Modifie la ville du salarié si la nouvelle valeur est valide."""
        if nouvelle_ville.strip() == "":
            print("La ville de l'employé ne peut pas être vide !")
        else:
            self.Ville = nouvelle_ville
            print("La ville a été modifié.")
    
    def afficher(self):
        """Affiche un résumé de création du salarié."""
        print(f"{self.Prenom} {self.Nom} a été ajouté(e) en tant que Salarié.")


class User(Salarie):
    """Classe représentant un utilisateur du système.
       Hérite des informations de base d’un salarié."""

    def __init__(self, nom, prenom, ville, role, login=None, password_hash=None, password_expiry=None, account_locked_until=None):
        """Initialise un utilisateur en appelant d'abord la classe parent."""
        
        # Appel explicite du constructeur de Salarie
        Salarie.__init__(self, nom, prenom, ville)
        
        # Ajout des propriétés spécifiques à un utilisateur
        self.Role = role
        self.Login = login
        self.Password_Hash = password_hash

    def generer_login(self):
        """Crée le login à partir de la première lettre du prénom + le nom complet."""
        
        # Première lettre du prénom (en minuscule)
        premiere_lettre = self.Prenom[0].lower()

        # Nom complet sans espaces, en minuscule
        nom_complet = self.Nom.replace(" ", "").lower()

        # Association pour créer le login par défaut
        self.Login = premiere_lettre + nom_complet
    
    def generer_mot_de_passe(self):
        """Génère un mot de passe temporaire aléatoire."""
        return secrets.token_urlsafe(12)
    
    def hacher_mot_de_passe(self, mot_de_passe_clair):
        """Transforme un mot de passe en hash SHA-256 pour stockage sécurisé."""
        
        # Création d'un objet SHA-256
        sha256 = hashlib.sha256()

        # Ajout du mot de passe dans le calcul du hash
        sha256.update(mot_de_passe_clair.encode('utf-8'))

        # Stockage du résultat final (hexadécimal)
        hash_pwd = sha256.hexdigest()
        self.Password_Hash = hash_pwd
    
    def verifier_mot_de_passe(self, mot_de_passe_clair):
        """Compare un mot de passe saisi avec le hash enregistré."""
        
        # Si aucun mot de passe stocké, vérification impossible
        if not self.Password_Hash:
            return False
        
        # Hachage du mot de passe saisi
        sha256 = hashlib.sha256()
        sha256.update(mot_de_passe_clair.encode('utf-8'))

        # Comparaison entre le hash calculé et celui enregistré
        return sha256.hexdigest() == self.Password_Hash
    
    def changer_mot_de_passe(self, ancien_mot_de_passe, nouveau_mot_de_passe):
        """Effectue la modification du mot de passe après vérification."""
        
        # L'ancien mot de passe doit correspondre au hash existant
        if not self.verifier_mot_de_passe(ancien_mot_de_passe):
            return False
        
        # Vérification rudimentaire de taille (peut être renforcée si besoin)
        if len(nouveau_mot_de_passe) < 4:
            print("Erreur : Le mot de passe doit contenir au moins 4 caractères.")
            return False
        
        # Hachage et stockage du nouveau mot de passe
        self.hacher_mot_de_passe(nouveau_mot_de_passe)
        return True
    
    def get_role(self):
        """Retourne le rôle attribué à l'utilisateur."""
        return self.Role
    
    def set_role(self, nouveau_role):
        """Change le rôle de l'utilisateur."""
        self.Role = nouveau_role
        print("Le Rôle a été modifié.")
    
    def Afficher_User(self):
        """Affiche les informations personnelles de l'utilisateur."""
        print("\n--- Fiche Utilisateur ---")
        print(f"Login        : {self.Login}")
        print(f"Nom          : {self.get_nom()}")
        print(f"Prénom       : {self.get_prenom()}")
        print(f"Ville        : {self.get_ville()}")
        print(f"Rôle         : {self.Role}")
