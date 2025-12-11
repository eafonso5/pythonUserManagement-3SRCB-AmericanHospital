import sqlite3
from classes import User
from datetime import datetime, timezone

class DatabaseManager:
    """Classe responsable de la gestion de la base SQLite.
       Contient toutes les opérations CRUD (Create, Read, Update, Delete)."""

    def __init__(self, nom_base="utilisateurs.db"):
        """Initialise la base de données en créant le fichier et la table si nécessaire."""
        self.nom_base = nom_base
        
        # Création de la table si elle n'existe pas déjà
        self.creer_table()

        # Initialisation d'un Super Admin s'il n'y a aucun utilisateur dans la base
        self.initialiser_super_admin()
    
    def get_connexion(self):
        """Retourne une nouvelle connexion à la base SQLite."""
        return sqlite3.connect(self.nom_base)
    
    def creer_table(self):
        """Crée la table principale 'utilisateurs' si elle n'existe pas."""
        
        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Création de la table avec les colonnes essentielles du système
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
        
        curseur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS unique_admin_superadmin_ville
            ON utilisateurs(ville)
            WHERE role IN ('Admin', 'Super Admin')
        """)
        
        connexion.commit()
        connexion.close()
    
    def initialiser_super_admin(self):
        """Crée un compte Super Admin par défaut si la base est vide."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # On vérifie combien d'utilisateurs existent actuellement dans la base
        curseur.execute("SELECT COUNT(*) FROM utilisateurs")
        nombre_users = curseur.fetchone()[0]
        
        connexion.close()
        
        # Si aucun utilisateur, on crée le Super Admin automatiquement
        if nombre_users == 0:
            print("\n" + "=" * 60)
            print(" PREMIÈRE UTILISATION - INITIALISATION")
            print("=" * 60)
            print("\nCréation du compte Super Admin par défaut...")

            # Création de l'objet User correspondant
            super_admin = User(
                nom="Admin",
                prenom="Super",
                ville="Paris",
                role="Super Admin",
                password_expiry="DATE('now' '+ 90 day')",
                account_locked_until="DATE('now')"
            )
            super_admin.Login = "superadmin"
            
            # Définition du mot de passe par défaut
            super_admin.hacher_mot_de_passe("admin")
            
            # Enregistrement dans la base
            self.ajouter_utilisateur(super_admin)
            
            print("✓ Compte créé avec succès !")
            print("\n  Login : superadmin")
            print("  Mot de passe : admin")
            print("\n⚠ IMPORTANT : Changez ce mot de passe après la première connexion.")
            print("=" * 60)
    
    def ajouter_utilisateur(self, user):
        """Ajoute un nouvel utilisateur dans la base de données."""

        try:
            connexion = self.get_connexion()
            curseur = connexion.cursor()
            
            # Insertion des données utilisateur dans la table
            curseur.execute("""
                INSERT INTO utilisateurs (
                    login, nom, prenom, ville, role, password_hash,
                    password_expiry, account_locked_until
                )
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+90 day'), datetime('now'))
            """,
            (user.Login, user.Nom, user.Prenom, user.Ville, user.Role, user.Password_Hash))

            connexion.commit()
            connexion.close()
            return True
        
        except sqlite3.IntegrityError as erreur:
            # Erreur si deux Admin/Super Admin sur la même ville
            message = str(erreur)
            if "unique_admin_superadmin_ville" in message:
                print(
                    f"Erreur : il existe déjà un Admin ou Super Admin pour la ville '{user.Ville}'.\n"
                    "La création de ce compte avec ce rôle est interdite.")
            else:
                print(f"Erreur d'intégrité (unicité) : {erreur}")
            return False
           
            
        
        except Exception as erreur:
            # Capture d'éventuelles erreurs SQLite
            print(f"Erreur lors de l'ajout : {erreur}")
            return False
    
    def rechercher_par_login(self, login, ville_visible=None):
        """Recherche un utilisateur dans la base grâce à son login."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Sélection de toutes les informations importantes du compte
        if ville_visible is None:
            curseur.execute("""
                SELECT login, nom, prenom, ville, role,
                    password_hash, password_expiry, account_locked_until
                FROM utilisateurs
                WHERE login = ?
            """, (login,))          
        
        else:
            curseur.execute("""
                SELECT login, nom, prenom, ville, role,
                    password_hash, password_expiry, account_locked_until
                FROM utilisateurs
                WHERE login = ? AND ville = ?
            """, (login, ville_visible))
        
        resultat = curseur.fetchone()
        connexion.close()
        
        if resultat:
            # Reconstruction d'un objet User à partir des données SQL
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
        
        # Aucun utilisateur trouvé
        return None
    
    def rechercher_par_nom_prenom(self, nom, prenom, ville_visible=None):
        """Recherche un utilisateur à partir d'un nom et d'un prénom."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        if ville_visible is None:
            curseur.execute("""
                SELECT login, nom, prenom, ville, role,
                    password_hash, password_expiry, account_locked_until
                FROM utilisateurs
                WHERE nom = ? AND prenom = ?
            """, (nom, prenom))
        
        else:
            curseur.execute("""
                SELECT login, nom, prenom, ville, role,
                    password_hash, password_expiry, account_locked_until
                FROM utilisateurs
                WHERE nom = ? AND prenom = ? AND ville = ?
            """, (nom, prenom, ville_visible))
        
        resultat = curseur.fetchone()
        connexion.close()
        
        if resultat:
            # Construction d'un User avec les données trouvées
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
        
    def lister_tous_utilisateurs(self, ville_visible=None):
        """Retourne la liste des utilisateurs présents dans la base, dans les villes autorisées ."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Sélection basique des champs nécessaires à l'affichage
        # si super admin, pas de filtre sur la ville
        if ville_visible is None:
            curseur.execute("""
                SELECT login, nom, prenom, ville, role
                FROM utilisateurs
                ORDER BY login
            """)
        # sinon, filtre sur la ville spécifiée
        else:
            curseur.execute("""
                SELECT login, nom, prenom, ville, role
                FROM utilisateurs
                WHERE ville = ?
                ORDER BY login
            """, (ville_visible,))
        
        resultats = curseur.fetchall()
        connexion.close()
        
        liste_users = []

        # On crée une liste d'objets User pour faciliter la gestion
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
        """Met à jour un ou plusieurs champs d'un utilisateur."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Construction dynamique de la requête SQL selon les champs modifiés
        champs_a_modifier = []
        valeurs = []
        
        if nouveau_nom:
            champs_a_modifier.append("nom = ?")
            valeurs.append(nouveau_nom)
        
        if nouveau_prenom:
            champs_a_modifier.append("prenom = ?")
            valeurs.append(nouveau_prenom)

        if nouvelle_ville:
            champs_a_modifier.append("ville = ?")
            valeurs.append(nouvelle_ville)
        
        if nouveau_role:
            champs_a_modifier.append("role = ?")
            valeurs.append(nouveau_role)
        
        if nouveau_hash:
            champs_a_modifier.append("password_hash = ?")
            valeurs.append(nouveau_hash)
            
        if nouvelle_expiration:
            champs_a_modifier.append("password_expiry = ?")
            valeurs.append(nouvelle_expiration)
        
        # Aucun champ à modifier, rien à faire
        if not champs_a_modifier:
            return False
        
        # Ajout du login en fin de paramètres
        valeurs.append(login)
        
        # Construction finale de la requête SQL
        requete = f"UPDATE utilisateurs SET {', '.join(champs_a_modifier)} WHERE login = ?"
        
        # Exécution et sauvegarde
        curseur.execute(requete, valeurs)
        connexion.commit()
        
        lignes_modifiees = curseur.rowcount
        connexion.close()
        
        # Retourne True si au moins une ligne a été modifiée
        return lignes_modifiees > 0
    
    def supprimer_utilisateur(self, login):
        """Supprime définitivement un utilisateur grâce à son login."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        curseur.execute("DELETE FROM utilisateurs WHERE login = ?", (login,))
        
        connexion.commit()
        lignes_supprimees = curseur.rowcount
        connexion.close()
        
        return lignes_supprimees > 0
    
    def bloquer_utilisateur(self, login):
        """Bloque un compte utilisateur pendant une durée définie (1 minute ici)."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()

        # Mise à jour du champ de verrouillage avec une date future
        curseur.execute("""
            UPDATE utilisateurs
            SET account_locked_until = datetime('now', '+1 minutes')
            WHERE login = ?
        """, (login,))

        connexion.commit()
        connexion.close()

    def existe_admin_ou_superadmin_dans_ville(self, ville):
        connexion = self.get_connexion()
        curseur = connexion.cursor()

        curseur.execute("""
            SELECT login, role 
            FROM utilisateurs
            WHERE ville = ?
            AND role IN ('Admin', 'Super Admin')
            LIMIT 1
        """, (ville,))

        row = curseur.fetchone()
        connexion.close()

        if row:
            return {"login": row[0], "role": row[1]}

        return None

    def verifier_bloquage_utilisateur(self, login):
        """Vérifie si un compte est bloqué.
           Retourne True si le compte est utilisable, False si toujours verrouillé."""

        connexion = self.get_connexion()
        curseur = connexion.cursor()
        
        # Récupération de la date de fin de blocage
        curseur.execute("""
            SELECT account_locked_until
            FROM utilisateurs
            WHERE login = ?
        """, (login,))
        
        resultats = curseur.fetchone()
        connexion.close()
        
        # Si aucun enregistrement, le compte n'est pas bloqué
        if resultats is None:
            return True
        
        # Conversion de la chaîne SQL en datetime Python
        verrou_until = datetime.strptime(resultats[0], "%Y-%m-%d %H:%M:%S")
        verrou_until = verrou_until.replace(tzinfo=timezone.utc)
        
        maintenant = datetime.now(timezone.utc)
        
        # Si la date de déblocage est passée, l'accès est autorisé
        if verrou_until <= maintenant:
            return True
        
        # Calcul du temps restant avant la prochaine tentative
        restant = verrou_until - maintenant
        secondes = int(restant.total_seconds())
        
        heures, reste = divmod(secondes, 3600)
        minutes, secondes = divmod(reste, 60)
        
        print("\n⚠ Votre compte est actuellement verrouillé.")
        print(f"Temps restant avant la prochaine tentative : {heures} heures, {minutes} minute(s) et {secondes} seconde(s).")
        
        return False
