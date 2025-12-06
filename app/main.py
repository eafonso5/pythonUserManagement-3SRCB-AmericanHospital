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
    
    # Permettre 3 tentatives de connexion
    tentatives = 3
    user_connecte = None
    
    while tentatives > 0 and not user_connecte:
        if tentatives < 3:
            print(f"\n⚠ Il vous reste {tentatives} tentative(s)")
        
        user_connecte = authentifier_utilisateur(db)
        
        if not user_connecte:
            tentatives -= 1
            if tentatives > 0:
                print("Veuillez réessayer.")
    
    if not user_connecte:
        print("\n" + "=" * 60)
        print("ACCÈS REFUSÉ - Nombre maximum de tentatives atteint")
        print("=" * 60)
        print("Programme terminé pour des raisons de sécurité.")
        return
    
    # Si authentification réussie, lancer le menu approprié
    menu_principal(db, user_connecte)


# Point d'entrée
if __name__ == "__main__":
    main()