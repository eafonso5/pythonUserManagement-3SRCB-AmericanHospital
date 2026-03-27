from fonctions_gestion import (
    creer_utilisateur, consulter_liste_utilisateurs, rechercher_utilisateur,
    modifier_utilisateur, supprimer_utilisateur, changer_mon_mot_de_passe,
    est_admin, consulter_profil
)
from gestion_fichiers import FileManager
from gestion_ftp import FTPManager, planifier_sauvegarde_vendredi


def afficher_menu_admin(user_connecte):
    """Affiche le menu destiné aux administrateurs."""

    # Affiche un en-tête indiquant le rôle et l'identité de l'utilisateur connecté
    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : ADMINISTRATEUR")
    print("=" * 60)

    # Affichage de toutes les options accessibles aux administrateurs
    print("\n1. Créer un nouvel utilisateur")
    print("2. Consulter la liste des utilisateurs")
    print("3. Rechercher un utilisateur")
    print("4. Modifier un utilisateur")
    print("5. Supprimer un utilisateur")
    print("6. Consulter mon profil")
    print("7. Changer mon mot de passe")
    print("8. Gestion technique des fichiers & FTP")
    print("9. Quitter")
    print("\n" + "=" * 60) 


def menu_technique(user_connecte):
    """Sous-menu pour la gestion locale des fichiers et la synchro FTP."""
    
    fm = FileManager(user_connecte.Ville)
    ftp_m = FTPManager(user_connecte.Login)

    while True:
        print(f"\n--- GESTION TECHNIQUE : {user_connecte.Ville} ---")
        print("1. Lister le contenu local")
        print("2. Créer un élément (Dossier ou Fichier)")
        print("3. Supprimer un fichier/dossier local")
        print("4. Synchroniser vers FTP (Paris)")
        print("5. Planifier sauvegarde vendredi 20h00")
        print("6. Retour au menu principal")
        
        choix = input("\nVotre choix : ").strip()

        match choix:
            case "1":
                contenu = fm.lister_contenu()
                print(f"\nContenu du dossier {user_connecte.Ville.lower()} :")
                if contenu:
                    for element in contenu:
                        print(f" - {element}")
                else:
                    print(" (Dossier vide)")

            case "2":
                print("\nQuel type d'élément souhaitez-vous créer ?")
                print("1. Dossier")
                print("2. Fichier")
                type_element = input("Votre choix (1 ou 2) : ").strip()

                if type_element == "1":
                    nom = input("Nom du nouveau dossier : ").strip()
                    if nom and fm.creer_repertoire(nom):
                        print(f"✓ Dossier '{nom}' créé avec succès.")
                elif type_element == "2":
                    nom = input("Nom du nouveau fichier (avec extension, ex: bilan.txt) : ").strip()
                    if nom and fm.creer_fichier_vide(nom):
                        print(f"✓ Fichier '{nom}' créé avec succès.")
                else:
                    print("Erreur : Type d'élément invalide.")

            case "3":
                nom = input("Nom de l'élément à supprimer (avec extension si fichier) : ").strip()
                confirm = input(f"Confirmer la suppression de '{nom}' ? (oui/non) : ").lower()
                if confirm == "oui":
                    if fm.supprimer_element(nom):
                        print(f"✓ '{nom}' supprimé.")

            case "4":
                fichier = input("Nom de l'élément à synchroniser (ex: bilan.txt) : ").strip()
                import os
                path_complet = os.path.join(fm.base_path, fichier)
                
                if os.path.exists(path_complet):
                    print(f"Tentative d'envoi de '{fichier}' vers le serveur FTP...")
                    if ftp_m.connecter():
                        if ftp_m.upload_versioning(path_complet, user_connecte.Ville):
                            print("✓ Synchronisation FTP réussie.")
                        ftp_m.deconnecter()
                    else:
                        print("Erreur : Impossible de se connecter au serveur FTP.")
                else:
                    print(f"Erreur : '{fichier}' n'existe pas dans votre répertoire local.")

            case "5":
                planifier_sauvegarde_vendredi()
                print("✓ Tâche planifiée : Vendredi à 20h00.")

            case "6":
                break
            
            case _:
                print("Choix invalide.")


def menu_administrateur(db, user_connecte):
    """Point d'entrée du menu administrateur.
       Boucle permettant d'exécuter les actions tant que l'utilisateur reste dans le menu."""

    while True:
        # On affiche systématiquement le menu avant chaque choix
        afficher_menu_admin(user_connecte)

        # Lecture du choix utilisateur
        choix = input("\nVotre choix : ").strip()
        
        # Gestion des actions via pattern matching (structure moderne Python)
        match choix:
            case "1":
                # Création d'un nouvel utilisateur
                creer_utilisateur(db, user_connecte)
        
            case "2":
                # Consultation de tous les comptes existants
                consulter_liste_utilisateurs(db, user_connecte)
        
            case "3":
                # Recherche ciblée dans les utilisateurs
                rechercher_utilisateur(db, user_connecte)
        
            case "4":
                # Modification d'un utilisateur existant
                modifier_utilisateur(db, user_connecte)
        
            case "5":
                # Suppression d'un compte
                supprimer_utilisateur(db, user_connecte)
        
            case "6":
                # Consultation des informations personnelles de l'administrateur
                consulter_profil(user_connecte)        
        
            case "7":
                # Changement du mot de passe personnel
                changer_mon_mot_de_passe(db, user_connecte)

            case "8":
                # Gestion technique fichiers et FTP
                menu_technique(user_connecte)
        
            case "9":
                # Sortie propre du menu administrateur
                print("Au revoir !")
                break
            
            case _:
                # Gestion d’une saisie invalide
                print("\nChoix invalide. Veuillez réessayer.")


def menu_utilisateur(db, user_connecte):
    """Menu réservé aux utilisateurs simples."""

    while True:
        # Affiche l’interface dédiée aux Users
        afficher_menu_user(user_connecte)

        # Récupération du choix
        choix = input("\nVotre choix : ").strip()
        
        match choix:
            case "1":
                # Affiche uniquement les informations du compte connecté
                consulter_profil(user_connecte)
        
            case "2":
                # L'utilisateur peut modifier son propre mot de passe
                changer_mon_mot_de_passe(db, user_connecte)
            
            case "3":
                # Quitte proprement le menu utilisateur
                print("Au revoir !")
                break
            
            case _:
                # Erreur de saisie
                print("\nChoix invalide. Veuillez réessayer.")


def menu_principal(db, user_connecte):
    """Redirige l'utilisateur vers le menu adapté en fonction de son rôle."""

    # Un admin ou super admin est envoyé vers le menu complet
    if est_admin(user_connecte):
        menu_administrateur(db, user_connecte)

    # Les utilisateurs standards sont envoyés vers le menu simplifié
    else:
        menu_utilisateur(db, user_connecte)
