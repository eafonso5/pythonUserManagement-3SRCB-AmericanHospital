import bcrypt
import secrets

class Salarie(object):
    """Classe de base pour tout employé de l'hôpital"""
    
    def __init__(self, nom, prenom, afficher_creation=True):
        """Constructeur de la classe Salarié"""
        if afficher_creation:
            print("Création d'un objet Salarié...")
        self.Nom = nom
        self.Prenom = prenom
    
    # Méthodes getter
    def get_nom(self):
        """Retourne le nom du salarié"""
        return self.Nom
    
    def get_prenom(self):
        """Retourne le prénom du salarié"""
        return self.Prenom
    
    # Méthodes setter
    def set_nom(self, nouveau_nom):
        """Modifie le nom du salarié"""
        if nouveau_nom.strip() == "":
            print("Le nom de l'employé ne peut pas être vide !!!!")
        else:
            self.Nom = nouveau_nom
            print("Le Nom a été modifié.")
    
    def set_prenom(self, nouveau_prenom):
        """Modifie le prénom du salarié"""
        if nouveau_prenom.strip() == "":
            print("Le prénom de l'employé ne peut pas être vide !!!!")
        else:
            self.Prenom = nouveau_prenom
            print("Le Prénom a été modifié.")
    
    def afficher(self):
        """Affiche les informations du salarié"""
        print(f"{self.Prenom} {self.Nom} a été ajouté(e) en tant que Salarié.")


#---------------------------------------------------------------------------------------------------#

class User(Salarie):
    """Classe User qui hérite de Salarié avec login et password"""
    
    def __init__(self, nom, prenom, role, login=None, password_hash=None, afficher_creation=True):
        """Constructeur de la classe User"""
        if afficher_creation:
            print("Création d'un objet User...")
        Salarie.__init__(self, nom, prenom, afficher_creation=False)
        
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
        """Hache le mot de passe avec bcrypt"""
        # Générer le sel et hacher le mot de passe en une seule opération
        salt = bcrypt.gensalt()
        hash_pwd = bcrypt.hashpw(mot_de_passe_clair.encode('utf-8'), salt)
        
        # Stocker le hash (qui contient déjà le sel)
        self.Password_Hash = hash_pwd.decode('utf-8')
    
    def verifier_mot_de_passe(self, mot_de_passe_clair):
        """Vérifie si le mot de passe est correct"""
        if not self.Password_Hash:
            return False
        
        # bcrypt gère automatiquement la comparaison avec le sel intégré
        return bcrypt.checkpw(
            mot_de_passe_clair.encode('utf-8'),
            self.Password_Hash.encode('utf-8')
        )
    
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
        print(f"Rôle         : {self.Role}")