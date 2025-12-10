from database import DatabaseManager
from fonctions_gestion import authentifier_utilisateur
from menu import menu_principal


def main():
    """Fonction principale du programme."""

    print("\n" + "=" * 60)
    print(" SYSTÈME DE GESTION DES UTILISATEURS")
    print(" American Hospital - Programme Patient-First")
    print("=" * 60)
    
    # Création du gestionnaire de base de données.
    # Cette étape initialise la connexion et crée la table si nécessaire.
    db = DatabaseManager()
    
    # Lancement de la procédure d’authentification.
    # Renvoie un objet User si l'identification est correcte.
    user_connecte = authentifier_utilisateur(db)
    
    # Une fois authentifié, on dirige l'utilisateur vers le menu approprié.
    # Le rôle du user déterminera quel type de menu sera affiché.
    menu_principal(db, user_connecte)


# Vérifie que ce fichier est exécuté directement.
# Cela permet d’éviter d’exécuter main() en cas d’importation du module.
if __name__ == "__main__":
    main()