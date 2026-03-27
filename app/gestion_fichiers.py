import os
import shutil
import logging

# Configuration des logs pour tracer les actions locales
logging.basicConfig(
    filename='operations.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FileManager:
    """Classe pour la gestion locale des fichiers, cloisonnée par ville."""

    def __init__(self, ville):
        """Initialise le répertoire de travail spécifique à la ville."""
        self.ville = ville
        # Création du dossier racine 'data_hospital' s'il n'existe pas
        self.base_path = os.path.join("data_hospital", ville.lower())
        
        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path)
                logging.info(f"Initialisation du répertoire local pour {ville}")
            except Exception as e:
                logging.error(f"Erreur initialisation dossier {ville}: {e}")

    def lister_contenu(self):
        """Liste les fichiers et dossiers du site local."""
        try:
            contenu = os.listdir(self.base_path)
            return contenu if contenu else []
        except Exception as e:
            logging.error(f"Erreur lors du listage ({self.ville}): {e}")
            return None

    def creer_repertoire(self, nom_dossier):
        """Crée un sous-dossier dans l'espace de la ville."""
        chemin = os.path.join(self.base_path, nom_dossier)
        try:
            os.makedirs(chemin, exist_ok=True)
            logging.info(f"Dossier créé : {nom_dossier} (Ville: {self.ville})")
            return True
        except Exception as e:
            logging.error(f"Erreur création dossier {nom_dossier}: {e}")
            return False

    def creer_fichier_vide(self, nom_fichier):
        """Crée un fichier texte vide avec encodage UTF-8."""
        chemin = os.path.join(self.base_path, nom_fichier)
        try:
            # Utilisation de l'encodage utf-8 pour une compatibilité maximale
            with open(chemin, 'w', encoding='utf-8') as f:
                pass
            logging.info(f"Fichier créé : {nom_fichier} (Ville: {self.ville})")
            return True
        except Exception as e:
            logging.error(f"Erreur création fichier {nom_fichier}: {e}")
            return False

    def supprimer_element(self, nom_element):
        """Supprime un fichier ou un dossier récursivement."""
        chemin = os.path.join(self.base_path, nom_element)
        try:
            if os.path.isdir(chemin):
                shutil.rmtree(chemin)
            else:
                os.remove(chemin)
            logging.info(f"Élément supprimé : {nom_element} (Ville: {self.ville})")
            return True
        except Exception as e:
            logging.error(f"Erreur suppression {nom_element}: {e}")
            return False

    def deplacer_ou_renommer(self, source, destination):
        """Déplace ou renomme un fichier/dossier local."""
        src_path = os.path.join(self.base_path, source)
        dst_path = os.path.join(self.base_path, destination)
        try:
            shutil.move(src_path, dst_path)
            logging.info(f"Déplacement : {source} -> {destination} (Ville: {self.ville})")
            return True
        except Exception as e:
            logging.error(f"Erreur déplacement {source}: {e}")
            return False
