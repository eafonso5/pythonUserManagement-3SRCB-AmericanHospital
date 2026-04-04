from ftplib import FTP
import os
import logging
import threading
from datetime import datetime, timedelta

# Racine du projet (dossier parent de app/)
_ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

class FTPManager:
    """Gestionnaire de synchronisation FTP configuré pour le serveur de test."""

    def __init__(self, current_user_login, host="127.0.0.1", port=2121):
        self.host = host
        self.port = port
        self.current_user = current_user_login
        self.ftp = None
        
        # Identifiants par défaut pour le test (admin / password)
        # On vérifie quand même si des variables d'environnement existent
        self.ftp_user = os.getenv("FTP_USER", "admin")
        self.ftp_pass = os.getenv("FTP_PASS", "password")

    def connecter(self):
        """Établit la connexion au serveur de test local."""
        try:
            self.ftp = FTP()
            # Connexion avec l'hôte et le port spécifique
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            
            logging.info(f"CONNEXION TEST RÉUSSIE : '{self.current_user}' connecté à {self.host}:{self.port}")
            return True
        except Exception as e:
            logging.error(f"ÉCHEC CONNEXION TEST : {self.current_user} sur {self.host}:{self.port} ({e})")
            print(f"\nErreur : Impossible de se connecter au serveur de test ({e})")
            return False

    def deconnecter(self):
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass

    def upload_versioning(self, local_path, ville):
        """
        Upload un fichier depuis data_hospital/[ville] vers le FTP.
        Le paramètre local_path doit être le chemin complet vers le fichier local.
        """
        if not self.ftp:
            return False
            
        try:
            # On s'assure que le fichier existe localement
            if not os.path.exists(local_path):
                logging.error(f"FICHIER INTROUVABLE : {local_path}")
                print(f"Erreur : Le fichier '{local_path}' est introuvable.")
                return False

            # SÉCURITÉ : On vérifie que ce n'est pas un dossier
            if os.path.isdir(local_path):
                logging.warning(f"TENTATIVE UPLOAD DOSSIER REFUSÉE : {local_path}")
                print("\nErreur : Le transfert de dossiers n'est pas encore supporté.")
                print("Veuillez sélectionner un fichier simple.")
                return False

            # Dossier cible sur le FTP (cloisonnement par ville)
            nom_ville = ville.lower()
            try:
                self.ftp.cwd(nom_ville)
            except:
                self.ftp.mkd(nom_ville)
                self.ftp.cwd(nom_ville)

            # Versioning avec horodatage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            nom_original = os.path.basename(local_path)
            nom_final_distant = f"{timestamp}_{nom_original}"

            # Transfert binaire
            with open(local_path, "rb") as file:
                self.ftp.storbinary(f"STOR {nom_final_distant}", file)

            logging.info(f"UPLOAD TEST RÉUSSI : {local_path} -> {nom_final_distant}")
            return True
        except Exception as e:
            logging.error(f"ERREUR UPLOAD TEST : {e}")
            return False

    def lister_contenu_ftp(self, ville):
        """Liste les fichiers présents dans le dossier de la ville sur le FTP."""
        if not self.ftp:
            return []
        try:
            nom_ville = ville.lower()
            try:
                self.ftp.cwd(nom_ville)
            except Exception:
                logging.warning(f"Dossier FTP '{nom_ville}' introuvable.")
                return []
            fichiers = self.ftp.nlst()
            logging.info(f"LISTING FTP : {ville} -> {len(fichiers)} élément(s).")
            return fichiers
        except Exception as e:
            logging.error(f"Erreur listing FTP ({ville}): {e}")
            return []

    def telecharger_fichier(self, nom_fichier, ville, destination_locale):
        """Télécharge un fichier depuis le dossier FTP de la ville."""
        if not self.ftp:
            return False
        try:
            nom_ville = ville.lower()
            try:
                self.ftp.cwd(nom_ville)
            except Exception:
                logging.error(f"Dossier FTP '{nom_ville}' introuvable.")
                return False
            chemin_local = os.path.join(destination_locale, nom_fichier)
            with open(chemin_local, "wb") as f:
                self.ftp.retrbinary(f"RETR {nom_fichier}", f.write)
            logging.info(f"DOWNLOAD FTP RÉUSSI : {nom_fichier} -> {chemin_local}")
            return True
        except Exception as e:
            logging.error(f"Erreur téléchargement FTP {nom_fichier}: {e}")
            return False


def _prochaine_sauvegarde_vendredi():
    """Calcule le datetime du prochain vendredi à 20h00."""
    now = datetime.now()
    jours_avant_vendredi = (4 - now.weekday()) % 7
    prochain = now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=jours_avant_vendredi)
    if prochain <= now:
        prochain += timedelta(weeks=1)
    return prochain


def sauvegarder_vers_ftp(ville, user_login):
    """Uploade tous les fichiers locaux de la ville vers le FTP,
    puis planifie automatiquement la prochaine exécution le vendredi à 20h00."""
    logging.info(f"SAUVEGARDE DÉMARRÉE : {ville}")
    base_path = os.path.join(_ROOT_DIR, "data_hospital", ville.lower())

    nb_ok, total = 0, 0
    if not os.path.exists(base_path):
        logging.warning(f"SAUVEGARDE : dossier local introuvable ({base_path})")
        total = -1
    else:
        ftp = FTPManager(user_login)
        if not ftp.connecter():
            logging.error("SAUVEGARDE ÉCHOUÉE : impossible de se connecter au FTP")
            total = -1
        else:
            fichiers = [f for f in os.listdir(base_path) if os.path.isfile(os.path.join(base_path, f))]
            total = len(fichiers)
            for fichier in fichiers:
                if ftp.upload_versioning(os.path.join(base_path, fichier), ville):
                    nb_ok += 1
            ftp.deconnecter()
            logging.info(f"SAUVEGARDE TERMINÉE : {nb_ok}/{total} fichier(s) ({ville})")

    # Planifie la prochaine exécution automatique (vendredi 20h00)
    prochain = _prochaine_sauvegarde_vendredi()
    delai = (prochain - datetime.now()).total_seconds()
    timer = threading.Timer(delai, sauvegarder_vers_ftp, args=[ville, user_login])
    timer.daemon = True
    timer.start()
    logging.info(f"PROCHAINE SAUVEGARDE : {ville} -> {prochain.strftime('%A %d/%m/%Y à %H:%M')}")

    return nb_ok, total, prochain
