import logging
import os

from fonctions_gestion import (
    creer_utilisateur, consulter_liste_utilisateurs, rechercher_utilisateur,
    modifier_utilisateur, supprimer_utilisateur, changer_mon_mot_de_passe,
    est_admin, est_superadmin, consulter_profil
)

VILLES = ["paris", "marseille", "rennes", "grenoble"]
from gestion_fichiers import FileManager
from gestion_ftp import FTPManager, sauvegarder_vers_ftp


def afficher_menu_admin(user_connecte):
    """Affiche le menu destiné aux administrateurs."""

    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : ADMINISTRATEUR")
    print("=" * 60)

    print("\n1. Créer un nouvel utilisateur")
    print("2. Consulter la liste des utilisateurs")
    print("3. Rechercher un utilisateur")
    print("4. Modifier un utilisateur")
    print("5. Supprimer un utilisateur")
    print("6. Consulter mon profil")
    print("7. Changer mon mot de passe")
    print("8. Quitter vers le menu principal")
    print("\n" + "=" * 60)


def afficher_menu_user(user_connecte):
    """Affiche le menu destiné aux utilisateurs standards."""

    print("\n" + "=" * 60)
    print(" GESTION DES UTILISATEURS - AMERICAN HOSPITAL")
    print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
    print(" Mode : UTILISATEUR")
    print("=" * 60)

    print("\n1. Consulter mon profil")
    print("2. Changer mon mot de passe")
    print("3. Quitter vers le menu principal")
    print("\n" + "=" * 60)


def _choisir_ville(ville_courante):
    """Permet au Super Admin de changer de ville. Retourne la ville sélectionnée."""
    print("\n--- CHANGER DE VILLE ---")
    for i, ville in enumerate(VILLES, 1):
        marqueur = " (actuelle)" if ville == ville_courante.lower() else ""
        print(f"{i}. {ville.capitalize()}{marqueur}")
    print("0. Annuler")

    choix = input("\nVotre choix : ").strip()
    if choix.isdigit() and 1 <= int(choix) <= len(VILLES):
        nouvelle_ville = VILLES[int(choix) - 1]
        logging.info(f"Super Admin : changement de ville -> {nouvelle_ville}")
        return nouvelle_ville.capitalize()
    return ville_courante


def menu_technique(user_connecte):
    """Sous-menu pour la gestion locale des fichiers et la synchro FTP."""

    ville_active = user_connecte.Ville
    fm = FileManager(ville_active)
    ftp_m = FTPManager(user_connecte.Login)

    while True:
        print(f"\n--- GESTION DES FICHIERS : {ville_active} ---")
        print("1. Lister le contenu local")
        print("2. Créer un élément (Dossier ou Fichier)")
        print("3. Supprimer un fichier/dossier local")
        print("4. Déplacer / renommer un élément")
        print("5. Copier un élément")
        print("6. Synchroniser vers FTP (upload)")
        print("7. Lister le contenu FTP")
        print("8. Télécharger depuis FTP")
        print("9. Sauvegarder dossier local vers FTP")
        if est_superadmin(user_connecte):
            print("c. Changer de ville")
        print("0. Retour au menu principal")

        choix = input("\nVotre choix : ").strip()

        match choix:
            case "1":
                lignes = fm.lister_arbre()
                print(f"\nContenu du dossier {ville_active.lower()} :")
                if lignes:
                    for ligne in lignes:
                        print(f" {ligne}")
                else:
                    print(" (Dossier vide)")

            case "2":
                print("\nQuel type d'élément souhaitez-vous créer ?")
                print("1. Dossier")
                print("2. Fichier")
                type_element = input("Votre choix (1 ou 2) : ").strip()

                if type_element == "1":
                    nom = input("Nom ou chemin du dossier (ex: archives/2024) : ").strip()
                    if nom and fm.creer_repertoire(nom):
                        print(f"Dossier '{nom}' créé.")
                elif type_element == "2":
                    nom = input("Nom ou chemin du fichier (ex: bilans/2024/rapport.txt) : ").strip()
                    if nom and fm.creer_fichier_vide(nom):
                        print(f"Fichier '{nom}' créé.")
                else:
                    print("Erreur : Type d'élément invalide.")

            case "3":
                nom = input("Nom de l'élément à supprimer (avec extension si fichier) : ").strip()
                confirm = input(f"Confirmer la suppression de '{nom}' ? (oui/non) : ").lower()
                if confirm == "oui":
                    if fm.supprimer_element(nom):
                        print(f"'{nom}' supprimé.")

            case "4":
                source = input("Nom de l'élément source : ").strip()
                destination = input("Nouveau nom / destination : ").strip()
                if source and destination:
                    if fm.deplacer_ou_renommer(source, destination):
                        print(f"'{source}' déplacé/renommé vers '{destination}'.")

            case "5":
                source = input("Nom de l'élément à copier : ").strip()
                destination = input("Nom de la copie : ").strip()
                if source and destination:
                    if fm.copier_element(source, destination):
                        print(f"'{source}' copié vers '{destination}'.")

            case "6":
                lignes = fm.lister_arbre()
                print(f"\nContenu local ({ville_active.lower()}) :")
                if lignes:
                    for ligne in lignes:
                        print(f" {ligne}")
                else:
                    print(" (Dossier vide)")
                fichier = input("\nNom du fichier ou dossier à envoyer vers le FTP : ").strip()
                path_complet = os.path.join(fm.base_path, fichier)

                if os.path.exists(path_complet):
                    print(f"Envoi de '{fichier}' vers le serveur FTP...")
                    if ftp_m.connecter():
                        if ftp_m.upload_versioning(path_complet, ville_active):
                            print("Synchronisation FTP réussie.")
                        ftp_m.deconnecter()
                    else:
                        print("Erreur : Impossible de se connecter au serveur FTP.")
                else:
                    print(f"Erreur : '{fichier}' n'existe pas dans votre répertoire local.")

            case "7":
                print(f"Récupération du contenu FTP pour {ville_active}...")
                if ftp_m.connecter():
                    fichiers = ftp_m.lister_contenu_ftp(ville_active)
                    ftp_m.deconnecter()
                    if fichiers:
                        print(f"\nContenu FTP ({ville_active}) :")
                        for f in fichiers:
                            print(f" - {f}")
                    else:
                        print(" (Dossier FTP vide ou introuvable)")
                else:
                    print("Erreur : Impossible de se connecter au serveur FTP.")

            case "8":
                nom_fichier = input("Nom du fichier à télécharger depuis le FTP : ").strip()
                if nom_fichier:
                    dest = fm.base_path
                    print(f"Téléchargement de '{nom_fichier}' vers {dest} ...")
                    if ftp_m.connecter():
                        if ftp_m.telecharger_fichier(nom_fichier, ville_active, dest):
                            print(f"'{nom_fichier}' téléchargé dans {dest}.")
                        ftp_m.deconnecter()
                    else:
                        print("Erreur : Impossible de se connecter au serveur FTP.")

            case "9":
                print("Sauvegarde en cours...")
                nb_ok, total, prochain = sauvegarder_vers_ftp(ville_active, user_connecte.Login)
                if total == -1:
                    print("Erreur : impossible de se connecter au serveur FTP.")
                else:
                    print(f"{nb_ok}/{total} élément(s) sauvegardé(s).")
                print(f"Prochaine sauvegarde automatique : {prochain.strftime('%A %d/%m/%Y à %H:%M')}.")

            case "c" if est_superadmin(user_connecte):
                nouvelle_ville = _choisir_ville(ville_active)
                if nouvelle_ville != ville_active:
                    ville_active = nouvelle_ville
                    fm = FileManager(ville_active)
                    print(f"Ville changée : {ville_active}")

            case "0":
                break

            case _:
                print("Choix invalide.")


def menu_administrateur(db, user_connecte):
    """Menu administrateur : gestion des utilisateurs."""

    while True:
        afficher_menu_admin(user_connecte)

        choix = input("\nVotre choix : ").strip()

        match choix:
            case "1":
                creer_utilisateur(db, user_connecte)

            case "2":
                consulter_liste_utilisateurs(db, user_connecte)

            case "3":
                rechercher_utilisateur(db, user_connecte)

            case "4":
                modifier_utilisateur(db, user_connecte)

            case "5":
                supprimer_utilisateur(db, user_connecte)

            case "6":
                consulter_profil(user_connecte)

            case "7":
                changer_mon_mot_de_passe(db, user_connecte)

            case "8":
                break

            case _:
                print("\nChoix invalide. Veuillez réessayer.")


def menu_utilisateur(db, user_connecte):
    """Menu réservé aux utilisateurs simples."""

    while True:
        afficher_menu_user(user_connecte)

        choix = input("\nVotre choix : ").strip()

        match choix:
            case "1":
                consulter_profil(user_connecte)

            case "2":
                changer_mon_mot_de_passe(db, user_connecte)

            case "3":
                break

            case _:
                print("\nChoix invalide. Veuillez réessayer.")


def menu_principal(db, user_connecte):
    """Pré-menu principal permettant de naviguer entre les grandes sections."""

    while True:
        print("\n" + "=" * 60)
        print(" === AMERICAN HOSPITAL - Patient-First ===")
        print(f" Connecté : {user_connecte.Login} ({user_connecte.Role})")
        print("=" * 60)
        print("\n1. Gestion des Utilisateurs")
        print("2. Gestion des Fichiers")
        print("0. Quitter")

        choix = input("\nVotre choix : ").strip()

        match choix:
            case "1":
                logging.info(f"Navigation Gestion Utilisateurs par {user_connecte.Login}")
                if est_admin(user_connecte):
                    menu_administrateur(db, user_connecte)
                else:
                    menu_utilisateur(db, user_connecte)

            case "2":
                if est_admin(user_connecte):
                    logging.info(f"Navigation Gestion Fichiers par {user_connecte.Login}")
                    menu_technique(user_connecte)
                else:
                    print("\nAccès refusé : cette section est réservée aux administrateurs.")

            case "0":
                print("\nAu revoir !")
                break

            case _:
                print("\nChoix invalide. Veuillez réessayer.")
