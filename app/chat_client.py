import socket
import threading
import sys
import os
import shutil

# Configuration par défaut (surchargeable par variables d'environnement)
HOTE = os.getenv("CHAT_HOST", "127.0.0.1")
PORT = int(os.getenv("CHAT_PORT", "5050"))

# Encodage utilisé pour tous les échanges réseau
ENCODAGE = "utf-8"


def _activer_ansi_windows():
    """Active l'interprétation des séquences ANSI dans la console Windows (mode VT).

    Sans cela, les codes d'effacement/positionnement s'afficheraient en clair
    sur d'anciennes consoles. Sans effet (et sans erreur) sur Linux/macOS."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def _largeur_terminal():
    """Largeur courante du terminal en colonnes (80 par défaut si indéterminée)."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def _afficher_a_droite(texte):
    """Affiche un texte justifié à droite du terminal (= messages de l'utilisateur).

    Si le texte est plus large que le terminal, rjust le laisse tel quel :
    il s'affiche alors normalement à gauche plutôt que d'être tronqué."""
    print(texte.rjust(_largeur_terminal()))


class ClientChat:
    """Client de chat interne : se connecte au serveur, envoie son pseudo,
       puis échange des messages. La réception se fait dans un thread séparé
       pour pouvoir écrire et recevoir en même temps."""

    def __init__(self, hote=HOTE, port=PORT):
        self.hote = hote
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Drapeau partagé indiquant si la connexion est active
        self.actif = True

        # Verrou pour éviter que l'affichage d'un message reçu (thread de réception)
        # ne s'entrelace avec le réaffichage de nos propres messages.
        self.verrou_affichage = threading.Lock()

    def connecter(self, pseudo):
        """Établit la connexion au serveur et envoie le pseudo."""
        try:
            self.socket.connect((self.hote, self.port))
            # Le premier message envoyé est le pseudo (attendu par le serveur)
            self.socket.send(pseudo.encode(ENCODAGE))
            return True
        except Exception as e:
            print(f"Erreur : impossible de se connecter à {self.hote}:{self.port} ({e})")
            return False

    def recevoir(self):
        """Boucle de réception des messages, exécutée dans un thread dédié."""
        while self.actif:
            try:
                donnees = self.socket.recv(1024)
                if not donnees:
                    # Le serveur a fermé la connexion
                    print("\nConnexion au serveur perdue.")
                    self.actif = False
                    break
                # Messages reçus : affichés à gauche (comportement par défaut)
                with self.verrou_affichage:
                    print(donnees.decode(ENCODAGE))
            except Exception:
                self.actif = False
                break

    def envoyer(self):
        """Boucle d'envoi : lit les saisies clavier et les transmet au serveur."""
        print("Vous êtes connecté. Tapez vos messages (/quit pour quitter).\n")
        while self.actif:
            try:
                message = input()
            except (EOFError, KeyboardInterrupt):
                message = "/quit"

            if not self.actif:
                break

            try:
                self.socket.send(message.encode(ENCODAGE))
            except Exception:
                print("Erreur : envoi impossible, connexion fermée.")
                self.actif = False
                break

            # On réaffiche notre propre message justifié à droite pour le distinguer
            # des messages reçus (à gauche). La ligne saisie (écho clavier) est
            # d'abord effacée : \033[F remonte d'une ligne, \033[2K l'efface.
            if message and message != "/quit":
                with self.verrou_affichage:
                    sys.stdout.write("\033[F\033[2K")
                    _afficher_a_droite(message)

            if message == "/quit":
                self.actif = False
                break

    def demarrer(self, pseudo):
        """Lance le client : connexion, thread de réception, boucle d'envoi."""
        # Nécessaire pour que l'alignement à droite fonctionne sous Windows
        _activer_ansi_windows()

        if not self.connecter(pseudo):
            return

        # Thread de réception en tâche de fond
        thread_reception = threading.Thread(target=self.recevoir)
        thread_reception.daemon = True
        thread_reception.start()

        # La boucle d'envoi occupe le thread principal
        self.envoyer()

        # Fermeture propre à la sortie
        try:
            self.socket.close()
        except Exception:
            pass
        print("Déconnecté du chat.")


if __name__ == "__main__":
    # Le pseudo peut être passé en argument (ex : python chat_client.py Benjamin),
    # sinon il est demandé de façon interactive.
    if len(sys.argv) > 1:
        pseudo = sys.argv[1]
    else:
        pseudo = input("Votre pseudo : ").strip()

    while not pseudo:
        pseudo = input("Le pseudo ne peut pas être vide. Votre pseudo : ").strip()

    ClientChat().demarrer(pseudo)
