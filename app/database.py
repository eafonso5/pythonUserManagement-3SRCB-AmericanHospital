import sqlite3
from classes import User
from datetime import datetime, timezone

class DatabaseManager:
    """Classe pour gérer la base de données SQLite"""
    
    def __init__(self, nom_base="utilisateurs.db"):
        """Initialise la connexion à la base de données"""
        self.nom_base = nom_base
        self.creer_table()
        self.initialiser_super_admin()
    
    def get_connexion(self):
        """Retourne une connexion à la base de données"""
        return sqlite3.connect(self.nom_base)
    
    def creer_table(self):
        """Crée la table utilisateurs si elle n'existe pas"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("""
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                ville TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_expiry DATE NOT NULL,
                account_locked_until DATE
            )
        """)
        
        connexion.commit()
        connexion.close()
    
    def initialiser_super_admin(self):
        """Crée le compte Super Admin par défaut si aucun utilisateur n'existe"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Vérifier s'il existe déjà des utilisateurs
        curseur.execute("SELECT COUNT(*) FROM utilisateurs")
        nombre_users = curseur.fetchone()[0]
        
        connexion.close()
        
        # Si aucun utilisateur, créer le Super Admin
        if nombre_users == 0:
            print("\n" + "=" * 60)
            print(" PREMIÈRE UTILISATION - INITIALISATION")
            print("=" * 60)
            print("\nCréation du compte Super Admin par défaut...")
            
            # Créer l'utilisateur Super Admin
            super_admin = User(nom="Admin", prenom="Super", ville="Paris", role="Super Admin", password_expiry="DATE('now' '+ 90 day')" , account_locked_until="DATE('now')")
            super_admin.Login = "superadmin"
            
            # Définir le mot de passe "admin"
            super_admin.hacher_mot_de_passe("admin")
            
            # Ajouter à la base de données
            self.ajouter_utilisateur(super_admin)
            
            print("✓ Compte créé avec succès !")
            print("\n  Login : superadmin")
            print("  Mot de passe : admin")
            print("\n⚠ IMPORTANT : Changez ce mot de passe après la première connexion.")
            print("=" * 60)
    
    def ajouter_utilisateur(self, user):
        """Ajoute un utilisateur dans la base de données"""
        try:
            connexion = self.get_connexion()
            curseur = connexion.cursor()
            
            curseur.execute("""
                INSERT INTO utilisateurs (
                    login, nom, prenom, ville, role, password_hash,
                    password_expiry, account_locked_until
                )
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+90 day'), datetime('now'))
            """,
            (user.Login,user.Nom,user.Prenom,user.Ville,user.Role,user.Password_Hash))

            connexion.commit()
            connexion.close()
            return True
        
        except sqlite3.IntegrityError:
            print(f"Erreur : Le login '{user.Login}' existe déjà.")
            return False
        except Exception as e:
            print(f"Erreur lors de l'ajout : {e}")
            return False
    
    def rechercher_par_login(self, login):
        """Recherche un utilisateur par son login"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("""
            SELECT login, nom, prenom, ville, role, password_hash, password_expiry, account_locked_until
            FROM utilisateurs
            WHERE login = ?
        """, (login,))
        
        resultat = curseur.fetchone()
        connexion.close()
        
        if resultat:
            # Créer un objet User à partir des données
            user = User(
                nom=resultat[1],
                prenom=resultat[2],
                ville=resultat[3],
                role=resultat[4],
                login=resultat[0],
                password_hash=resultat[5],
                password_expiry=resultat[6],
                account_locked_until=resultat[7]
            )
            return user
        
        return None
    
    def rechercher_par_nom_prenom(self, nom, prenom):
        """Recherche un utilisateur par nom ET prénom"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("""
            SELECT login, nom, prenom, ville, role, password_hash, password_expiry, account_locked_until
            FROM utilisateurs
            WHERE nom = ? AND prenom = ?
        """, (nom, prenom))
        
        resultat = curseur.fetchone()
        connexion.close()
        
        if resultat:
            user = User(
                nom=resultat[1],
                prenom=resultat[2],
                ville=resultat[3],
                role=resultat[4],
                login=resultat[0],
                password_hash=resultat[5],
                password_expiry=resultat[6],
                account_locked_until=resultat[7]
            )
            return user
        
        return None
        
    def lister_tous_utilisateurs(self):
        """Retourne la liste de tous les utilisateurs"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("""
            SELECT login, nom, prenom, ville, role
            FROM utilisateurs
            ORDER BY login
        """)
        
        resultats = curseur.fetchall()
        connexion.close()
        
        liste_users = []
        for row in resultats:
            user = User(
                nom=row[1],
                prenom=row[2],
                ville=row[3],
                role=row[4],
                login=row[0]
            )
            liste_users.append(user)
        
        return liste_users
    
    def modifier_utilisateur(self, login, nouveau_nom=None, nouveau_prenom=None, 
                            nouvelle_ville=None, nouveau_role=None, nouveau_hash=None, nouvelle_expiration=None):
        """Modifie les informations d'un utilisateur"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Construire la requête dynamiquement
        champs_a_modifier = []
        valeurs = []
        
        if nouveau_nom: # Modifier le nom
            champs_a_modifier.append("nom = ?")
            valeurs.append(nouveau_nom)
        
        if nouveau_prenom: # Modifier le prénom
            champs_a_modifier.append("prenom = ?")
            valeurs.append(nouveau_prenom)

        if nouvelle_ville: # Modifier la ville
            champs_a_modifier.append("ville = ?")
            valeurs.append(nouvelle_ville)
        
        if nouveau_role: # Modifier le rôle
            champs_a_modifier.append("role = ?")
            valeurs.append(nouveau_role)
        
        if nouveau_hash: # Modifier le mot de passe
            champs_a_modifier.append("password_hash = ?")
            valeurs.append(nouveau_hash)
            
        if nouvelle_expiration: # Modifier la date d'expiration du mot de passe
            champs_a_modifier.append("password_expiry = ?")
            valeurs.append(nouvelle_expiration)
        
        if not champs_a_modifier:
            return False
        
        valeurs.append(login)
        requete = f"UPDATE utilisateurs SET {', '.join(champs_a_modifier)} WHERE login = ?"
        
        curseur.execute(requete, valeurs)
        connexion.commit()
        
        lignes_modifiees = curseur.rowcount
        connexion.close()
        
        return lignes_modifiees > 0
    
    def supprimer_utilisateur(self, login):
        """Supprime un utilisateur de la base de données"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("DELETE FROM utilisateurs WHERE login = ?", (login,))
        
        connexion.commit()
        lignes_supprimees = curseur.rowcount
        connexion.close()
        
        return lignes_supprimees > 0
    
    def bloquer_utilisateur(self, login):
        """Bloque la connexion pendant 1 minute."""
        connexion = self.get_connexion()
        curseur = connexion.cursor()

        curseur.execute("""
            UPDATE utilisateurs
            SET account_locked_until = datetime('now', '+1 minutes')
            WHERE login = ?
            """, 
        (login,)
        )

        connexion.commit()
        connexion.close()

    def verifier_bloquage_utilisateur(self,login):
        """Vérifie si le compte n'est PAS bloqué. True si connexion possible"""
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("""
            SELECT account_locked_until
            FROM utilisateurs
            WHERE login = ?
        """, (login,))
        
        resultats = curseur.fetchone()
        connexion.close()
        
        if resultats == None:
            return True
        
        verrou_until = datetime.strptime(resultats[0], "%Y-%m-%d %H:%M:%S")
        verrou_until = verrou_until.replace(tzinfo=timezone.utc)

        valid = verrou_until <= datetime.now(timezone.utc)

        return valid