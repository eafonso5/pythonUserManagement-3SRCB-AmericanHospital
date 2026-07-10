import socket
import threading
import sys
import os

# Configuration par défaut (surchargeable par variables d'environnement)
HOTE = os.getenv("CHAT_HOST", "127.0.0.1")
PORT = int(os.getenv("CHAT_PORT", "5050"))

# Encodage utilisé pour tous les échanges réseau
ENCODAGE = "utf-8"


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

            if message == "/quit":
                self.actif = False
                break

    def demarrer(self, pseudo):
        """Lance le client : connexion, thread de réception, boucle d'envoi."""
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
