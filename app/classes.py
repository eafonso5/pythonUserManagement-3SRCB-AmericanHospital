import secrets
import hashlib

class Salarie(object):
    """Classe de base pour tout employé de l'hôpital"""
    
    def __init__(self, nom, prenom, ville):
        """Constructeur de la classe Salarié"""
        self.Nom = nom
        self.Prenom = prenom
        self.Ville = ville
    
    # Méthodes getter
    def get_nom(self):
        """Retourne le nom du salarié"""
        return self.Nom
    
    def get_prenom(self):
        """Retourne le prénom du salarié"""
        return self.Prenom
    
    def get_ville(self):
        """Retourne la ville du salarié"""
        return self.Ville
    
    # Méthodes setter
    def set_nom(self, nouveau_nom):
        """Modifie le nom du salarié"""
        if nouveau_nom.strip() == "":
            print("Le nom de l'employé ne peut pas être vide !")
        else:
            self.Nom = nouveau_nom
            print("Le Nom a été modifié.")
    
    def set_prenom(self, nouveau_prenom):
        """Modifie le prénom du salarié"""
        if nouveau_prenom.strip() == "":
            print("Le prénom de l'employé ne peut pas être vide !")
        else:
            self.Prenom = nouveau_prenom
            print("Le Prénom a été modifié.")

    def set_ville(self, nouvelle_ville):
        """Modifie la ville du salarié"""
        if nouvelle_ville.strip() == "":
            print("La ville de l'employé ne peut pas être vide !")
        else:
            self.Ville = nouvelle_ville
            print("La ville a été modifié.")
    
    def afficher(self):
        """Affiche les informations du salarié"""
        print(f"{self.Prenom} {self.Nom} a été ajouté(e) en tant que Salarié.")


#---------------------------------------------------------------------------------------------------#

class User(Salarie):
    """Classe User qui hérite de Salarié avec login et password"""
    
    def __init__(self, nom, prenom, ville, role, login=None, password_hash=None):
        """Constructeur de la classe User"""
        Salarie.__init__(self, nom, prenom, ville)
        
        self.Role = role
        self.Login = login if login else self.generer_login()
        self.Password_Hash = password_hash
    
    def generer_login(self):
        """Génère le login : première lettre du prénom + nom"""
        premiere_lettre = self.Prenom[0].lower()
        nom_complet = self.Nom.replace(" ", "").lower()
        return premiere_lettre + nom_complet
    
    def generer_mot_de_passe(self):
        """Génère un mot de passe aléatoire"""
        return secrets.token_urlsafe(12)
    
    def hacher_mot_de_passe(self, mot_de_passe_clair):
        """Hache le mot de passe avec sha256"""
        sha256 = hashlib.sha256()
        sha256.update(mot_de_passe_clair.encode('utf-8'))
        hash_pwd = sha256.hexdigest()
        
        # Stocker le hash
        self.Password_Hash = hash_pwd
    
    def verifier_mot_de_passe(self, mot_de_passe_clair):
        """Vérifie si le mot de passe est correct"""
        if not self.Password_Hash:
            return False
        
        sha256 = hashlib.sha256()
        sha256.update(mot_de_passe_clair.encode('utf-8'))
        return sha256.hexdigest() == self.Password_Hash
    
    def changer_mot_de_passe(self, ancien_mot_de_passe, nouveau_mot_de_passe):
        """Change le mot de passe après vérification de l'ancien"""
        # Vérifier l'ancien mot de passe
        if not self.verifier_mot_de_passe(ancien_mot_de_passe):
            return False
        
        # Vérifier que le nouveau mot de passe est valide
        if len(nouveau_mot_de_passe) < 4:
            print("Erreur : Le mot de passe doit contenir au moins 4 caractères.")
            return False
        
        # Hacher et sauvegarder le nouveau mot de passe
        self.hacher_mot_de_passe(nouveau_mot_de_passe)
        return True
    
    def get_role(self):
        """Retourne le rôle de l'utilisateur"""
        return self.Role
    
    def set_role(self, nouveau_role):
        """Modifie le rôle de l'utilisateur"""
        self.Role = nouveau_role
        print("Le Rôle a été modifié.")
    
    def Afficher_User(self):
        """Affiche les informations de l'utilisateur"""
        print("\n--- Fiche Utilisateur ---")
        print(f"Login        : {self.Login}")
        print(f"Nom          : {self.get_nom()}")
        print(f"Prénom       : {self.get_prenom()}")
        print(f"Ville        : {self.get_ville()}")
        print(f"Rôle         : {self.Role}")