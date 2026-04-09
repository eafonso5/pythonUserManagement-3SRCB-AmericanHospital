from ftplib import FTP
import io
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

        # Identifiants de connexion, surchargés par variables d'environnement si disponibles
        self.ftp_user = os.getenv("FTP_USER", "admin")
        self.ftp_pass = os.getenv("FTP_PASS", "password")

    def connecter(self):
        """Établit la connexion au serveur FTP local."""
        try:
            self.ftp = FTP()
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            logging.info(f"CONNEXION FTP RÉUSSIE : '{self.current_user}' connecté à {self.host}:{self.port}")
            return True
        except Exception as e:
            logging.error(f"ÉCHEC CONNEXION FTP : {self.current_user} sur {self.host}:{self.port} ({e})")
            print(f"\nErreur : Impossible de se connecter au serveur de test ({e})")
            return False

    def deconnecter(self):
        """Ferme proprement la connexion FTP si elle est active."""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass

    def _naviguer_vers(self, chemin_ftp):
        """Navigue vers un chemin FTP absolu en créant les dossiers manquants (usage upload uniquement)."""
        parties = [p for p in chemin_ftp.strip("/").split("/") if p]

        # Réinitialisation à la racine avant navigation pour éviter les doublons de chemin
        self.ftp.cwd("/")
        for partie in parties:
            try:
                self.ftp.cwd(partie)
            except Exception:
                # Le dossier n'existe pas : création avant d'y entrer
                self.ftp.mkd(partie)
                self.ftp.cwd(partie)

    def _naviguer_lecture(self, chemin_ftp):
        """Navigue vers un chemin FTP absolu en lecture seule. Lève une exception si un segment est introuvable."""
        parties = [p for p in chemin_ftp.strip("/").split("/") if p]
        self.ftp.cwd("/")
        for partie in parties:
            try:
                self.ftp.cwd(partie)
            except Exception:
                raise FileNotFoundError(f"Chemin FTP introuvable : '{chemin_ftp}' (segment manquant : '{partie}')")

    def upload_versioning(self, local_path, ville):
        """Upload un fichier ou un dossier vers le FTP avec horodatage dans le nom."""
        if not self.ftp:
            return False
        if not os.path.exists(local_path):
            logging.error(f"INTROUVABLE : {local_path}")
            print(f"Erreur : '{local_path}' est introuvable.")
            return False

        # Construction du nom versionné avec horodatage au format AAAAMMJJ_HHMM
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        nom_original = os.path.basename(local_path)
        nom_versionne = f"{timestamp}_{nom_original}"
        nom_ville = ville.lower()

        try:
            if os.path.isdir(local_path):
                self._upload_dossier(local_path, nom_ville, nom_versionne)
            else:
                self._naviguer_vers(nom_ville)
                with open(local_path, "rb") as f:
                    self.ftp.storbinary(f"STOR {nom_versionne}", f)
                logging.info(f"UPLOAD FICHIER : {local_path} -> {nom_ville}/{nom_versionne}")
            return True
        except Exception as e:
            logging.error(f"ERREUR UPLOAD : {e}")
            return False

    def _upload_dossier(self, local_path, nom_ville, nom_racine_ftp):
        """Upload récursif d'un dossier vers le FTP. Retourne le nombre de fichiers envoyés."""
        nb_ok = 0
        for racine, sous_dossiers, fichiers in os.walk(local_path):

            # Calcul du chemin FTP cible relatif à la racine de l'arborescence locale
            chemin_relatif = os.path.relpath(racine, local_path)
            if chemin_relatif == ".":
                ftp_courant = f"{nom_ville}/{nom_racine_ftp}"
            else:
                ftp_courant = f"{nom_ville}/{nom_racine_ftp}/{chemin_relatif.replace(os.sep, '/')}"

            self._naviguer_vers(ftp_courant)

            # Pré-création des sous-dossiers pour éviter les erreurs lors du dépôt des fichiers
            for d in sous_dossiers:
                try:
                    self.ftp.mkd(d)
                except Exception:
                    pass

            # Envoi de chaque fichier du niveau courant
            for fichier in fichiers:
                chemin_local = os.path.join(racine, fichier)
                try:
                    with open(chemin_local, "rb") as f:
                        self.ftp.storbinary(f"STOR {fichier}", f)
                    nb_ok += 1
                except Exception as e:
                    logging.error(f"Erreur upload {chemin_local}: {e}")

        logging.info(f"UPLOAD DOSSIER : {local_path} -> {nom_ville}/{nom_racine_ftp} ({nb_ok} fichiers)")
        return nb_ok

    def _nom_sauvegarde(self, prefixe):
        """Retourne le nom du dossier de sauvegarde au format AAAAMMJJ_HHMM_prefixe."""
        return datetime.now().strftime(f"%Y%m%d_%H%M_{prefixe}")

    def lister_contenu_ftp(self, ville):
        """Liste les entrées présentes dans le dossier de la ville sur le FTP."""
        if not self.ftp:
            return []
        try:
            self._naviguer_vers(ville.lower())

            # nlst() peut retourner des chemins complets selon le serveur, on conserve uniquement le nom
            entrees = self.ftp.nlst()
            fichiers = [os.path.basename(e) for e in entrees]
            logging.info(f"LISTING FTP : {ville} -> {len(fichiers)} élément(s).")
            return fichiers
        except Exception as e:
            logging.error(f"Erreur listing FTP ({ville}): {e}")
            return []

    def lister_arbre_ftp(self, ville, prefixe=""):
        """Liste récursivement le contenu FTP sous forme d'arbre indenté (même format que lister_arbre local)."""
        if not self.ftp:
            return []
        try:
            self._naviguer_vers(ville.lower())
            return self._lister_arbre_ftp_recursif(prefixe)
        except Exception as e:
            logging.error(f"Erreur listing arbre FTP ({ville}): {e}")
            return []

    def _lister_arbre_ftp_recursif(self, prefixe=""):
        """Parcourt récursivement le répertoire FTP courant et retourne les lignes de l'arbre."""
        lignes = []
        try:
            entrees = sorted([os.path.basename(e) for e in self.ftp.nlst()])
        except Exception:
            return lignes

        for entree in entrees:
            if self._est_dossier_ftp(entree):
                lignes.append(f"{prefixe}[D] {entree}/")
                self.ftp.cwd(entree)
                lignes.extend(self._lister_arbre_ftp_recursif(prefixe + "    "))
                self.ftp.cwd("..")
            else:
                lignes.append(f"{prefixe}[F] {entree}")
        return lignes

    def _est_dossier_ftp(self, nom):
        """Retourne True si l'entrée FTP courante est un dossier, False si c'est un fichier."""
        try:
            self.ftp.cwd(nom)
            self.ftp.cwd("..")
            return True
        except Exception:
            return False

    def _telecharger_dossier(self, nom_ftp, destination_locale):
        """Télécharge récursivement un dossier FTP vers le système local."""
        dossier_local = os.path.join(destination_locale, nom_ftp)
        os.makedirs(dossier_local, exist_ok=True)
        self.ftp.cwd(nom_ftp)

        entrees = [os.path.basename(e) for e in self.ftp.nlst()]
        for entree in entrees:
            if self._est_dossier_ftp(entree):
                self._telecharger_dossier(entree, dossier_local)
            else:
                chemin_local = os.path.join(dossier_local, entree)
                # Téléchargement en mémoire d'abord pour éviter de créer un fichier vide en cas d'erreur
                buf = io.BytesIO()
                self.ftp.retrbinary(f"RETR {entree}", buf.write)
                with open(chemin_local, "wb") as f:
                    f.write(buf.getvalue())

        self.ftp.cwd("..")

    def telecharger_fichier(self, nom_fichier, ville, destination_locale):
        """Télécharge un fichier ou un dossier depuis le dossier FTP de la ville vers le dossier local.
        nom_fichier peut contenir des sous-chemins (ex: '20240101_1200_backup/patients/file.csv')."""
        if not self.ftp:
            return False
        try:
            # Décomposition du chemin : navigation jusqu'au répertoire parent, puis action sur la cible
            parties = nom_fichier.replace("\\", "/").strip("/").split("/")
            nom_cible = parties[-1]
            sous_chemin = "/".join(parties[:-1])

            chemin_ftp = ville.lower()
            if sous_chemin:
                chemin_ftp = f"{chemin_ftp}/{sous_chemin}"

            # Navigation en lecture seule : lève une exception si le chemin parent n'existe pas sur le FTP
            self._naviguer_lecture(chemin_ftp)

            # Vérification explicite de l'existence de la cible dans le répertoire courant
            entrees = [os.path.basename(e) for e in self.ftp.nlst()]
            if nom_cible not in entrees:
                msg = f"'{nom_fichier}' est introuvable sur le serveur FTP."
                logging.error(f"DOWNLOAD FTP : {msg}")
                print(f"\nErreur : {msg}")
                return False

            if self._est_dossier_ftp(nom_cible):
                self._telecharger_dossier(nom_cible, destination_locale)
                logging.info(f"DOWNLOAD FTP RÉUSSI (dossier) : {nom_fichier} -> {destination_locale}")
            else:
                # Téléchargement en mémoire d'abord pour éviter de créer un fichier vide en cas d'erreur
                buf = io.BytesIO()
                self.ftp.retrbinary(f"RETR {nom_cible}", buf.write)
                chemin_local = os.path.join(destination_locale, nom_cible)
                with open(chemin_local, "wb") as f:
                    f.write(buf.getvalue())
                logging.info(f"DOWNLOAD FTP RÉUSSI (fichier) : {nom_fichier} -> {chemin_local}")
            return True
        except FileNotFoundError as e:
            logging.error(f"DOWNLOAD FTP : {e}")
            print(f"\nErreur : {e}")
            return False
        except Exception as e:
            logging.error(f"Erreur téléchargement FTP {nom_fichier}: {e}")
            print(f"\nErreur lors du téléchargement de '{nom_fichier}' : {e}")
            return False


def _prochaine_sauvegarde_vendredi():
    """Calcule le datetime du prochain vendredi à 20h00."""
    now = datetime.now()
    jours_avant_vendredi = (4 - now.weekday()) % 7
    prochain = now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=jours_avant_vendredi)

    # Si on est déjà vendredi après 20h00, on reporte à la semaine suivante
    if prochain <= now:
        prochain += timedelta(weeks=1)
    return prochain


def sauvegarder_vers_ftp(ville, user_login, prefixe="automatic_saving"):
    """Uploade le dossier local de la ville vers un dossier versionné sur le FTP,
    puis planifie automatiquement la prochaine exécution le vendredi à 20h00."""
    logging.info(f"SAUVEGARDE DÉMARRÉE : {ville} ({prefixe})")
    base_path = os.path.join(_ROOT_DIR, "data_hospital", ville.lower())

    nb_ok, nom_sauvegarde = 0, None

    # Vérification de l'existence du dossier local avant toute tentative de connexion FTP
    if not os.path.exists(base_path):
        logging.warning(f"SAUVEGARDE : dossier local introuvable ({base_path})")
        nb_ok = -1
    else:
        ftp = FTPManager(user_login)
        if not ftp.connecter():
            logging.error("SAUVEGARDE ÉCHOUÉE : impossible de se connecter au FTP")
            nb_ok = -1
        else:
            # Génération du nom versionné et upload de l'arborescence complète du dossier ville
            nom_sauvegarde = ftp._nom_sauvegarde(prefixe)
            nb_ok = ftp._upload_dossier(base_path, ville.lower(), nom_sauvegarde)
            ftp.deconnecter()
            logging.info(f"SAUVEGARDE TERMINÉE : {nb_ok} fichier(s) -> {ville}/{nom_sauvegarde}")

    # Planification de la prochaine exécution automatique (vendredi 20h00)
    prochain = _prochaine_sauvegarde_vendredi()
    delai = (prochain - datetime.now()).total_seconds()
    timer = threading.Timer(delai, sauvegarder_vers_ftp, args=[ville, user_login, "automatic_saving"])
    timer.daemon = True
    timer.start()
    logging.info(f"PROCHAINE SAUVEGARDE : {ville} -> {prochain.strftime('%A %d/%m/%Y à %H:%M')}")

    return nb_ok, nom_sauvegarde, prochain
