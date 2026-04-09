import os
from database import DatabaseManager
from fonctions_gestion import authentifier_utilisateur
from gestion_ftp import demarrer_sauvegarde_auto
from menu import menu_principal
import logging

# Liste des villes disponibles dans l'application
VILLES = ["paris", "marseille", "rennes", "grenoble"]

# Racine du projet (dossier parent de app/)
ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def initialiser_dossiers():
    """Crée les dossiers locaux data_hospital/[ville] s'ils n'existent pas."""
    for ville in VILLES:
        chemin = os.path.join(ROOT_DIR, "data_hospital", ville)
        os.makedirs(chemin, exist_ok=True)
    logging.info("Dossiers locaux initialisés.")


def main():
    """Fonction principale du programme."""

    # Configuration du système de logs pour toute la session
    logging.basicConfig(
        filename='operations.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Démarrage de l'application - Session Utilisateur")

    # Création des dossiers locaux au démarrage si absents
    initialiser_dossiers()

    print("\n" + "=" * 60)
    print(" SYSTÈME DE GESTION DES UTILISATEURS")
    print(" American Hospital - Programme Patient-First")
    print("=" * 60)

    # Initialisation du gestionnaire de base de données
    db = DatabaseManager()

    # Authentification de l'utilisateur avant accès au menu
    user_connecte = authentifier_utilisateur(db)

    # Planification automatique des sauvegardes FTP pour toutes les villes
    for ville in VILLES:
        demarrer_sauvegarde_auto(ville, user_connecte.Login)

    # Redirection vers le menu principal selon le rôle de l'utilisateur
    menu_principal(db, user_connecte)


# Exécution directe uniquement, pas lors d'une importation du module
if __name__ == "__main__":
    main()
