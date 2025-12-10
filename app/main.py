from database import DatabaseManager
from fonctions_gestion import authentifier_utilisateur
from menu import menu_principal


def main():
    """Fonction principale du programme"""
    print("\n" + "=" * 60)
    print(" SYSTÈME DE GESTION DES UTILISATEURS")
    print(" American Hospital - Programme Patient-First")
    print("=" * 60)
    
    # Initialiser la base de données
    db = DatabaseManager()
    
    user_connecte = authentifier_utilisateur(db)
    
    # Si authentification réussie, lancer le menu approprié
    menu_principal(db, user_connecte)


# Point d'entrée
if __name__ == "__main__":
    main()