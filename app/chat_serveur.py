import socket
import threading
import logging
import os

# Configuration du serveur (surchargeable par variables d'environnement)
HOTE = os.getenv("CHAT_HOST", "127.0.0.1")
PORT = int(os.getenv("CHAT_PORT", "5050"))

# Nombre maximum de clients connectés simultanément (sujet : 1 serveur + 4 clients)
MAX_CLIENTS = 4

# Encodage utilisé pour tous les échanges réseau
ENCODAGE = "utf-8"


class ServeurChat:
    """Serveur de chat interne : accepte plusieurs clients et diffuse les messages
       à tout le monde (discussion de groupe). Chaque client est géré dans son propre thread."""

    def __init__(self, hote=HOTE, port=PORT):
        self.hote = hote
        self.port = port

        # Dictionnaire {socket_client: pseudo} des clients connectés
        self.clients = {}

        # Verrou pour protéger l'accès concurrent au dictionnaire des clients
        self.verrou = threading.Lock()

        # Socket serveur principal
        self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Permet de relancer le serveur immédiatement après un arrêt (réutilisation du port)
        self.socket_serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def demarrer(self):
        """Lance le serveur et attend les connexions entrantes."""
        try:
            self.socket_serveur.bind((self.hote, self.port))
            self.socket_serveur.listen()
        except Exception as e:
            logging.error(f"CHAT SERVEUR : impossible de démarrer ({e})")
            print(f"Erreur : impossible de démarrer le serveur ({e})")
            return

        print(f"Serveur de chat démarré sur {self.hote}:{self.port}")
        print(f"En attente de connexions (max {MAX_CLIENTS} clients)... [Ctrl+C pour arrêter]")
        logging.info(f"CHAT SERVEUR : démarré sur {self.hote}:{self.port}")

        try:
            while True:
                # Attente bloquante d'un nouveau client
                client, adresse = self.socket_serveur.accept()

                # Refus si le nombre maximum de clients est déjà atteint
                with self.verrou:
                    nb_clients = len(self.clients)
                if nb_clients >= MAX_CLIENTS:
                    try:
                        client.send("Serveur plein, réessayez plus tard.".encode(ENCODAGE))
                        client.close()
                    except Exception:
                        pass
                    logging.warning(f"CHAT SERVEUR : connexion refusée (serveur plein) {adresse}")
                    continue

                # Un thread dédié par client pour gérer ses messages en parallèle
                thread = threading.Thread(target=self.gerer_client, args=(client, adresse))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")
            logging.info("CHAT SERVEUR : arrêté par l'administrateur.")
        finally:
            self.socket_serveur.close()

    def gerer_client(self, client, adresse):
        """Gère un client : réception du pseudo puis boucle de réception des messages."""
        pseudo = None
        try:
            # Le tout premier message envoyé par le client est son pseudo
            pseudo = client.recv(1024).decode(ENCODAGE).strip()
            if not pseudo:
                client.close()
                return

            # Ajout du client à la liste partagée (sous verrou)
            with self.verrou:
                self.clients[client] = pseudo

            logging.info(f"CHAT SERVEUR : '{pseudo}' connecté depuis {adresse}")
            self.diffuser(f"*** {pseudo} a rejoint la discussion ***", expediteur=None)
            self.envoyer_liste_membres()

            # Boucle de réception des messages de ce client
            while True:
                donnees = client.recv(1024)
                if not donnees:
                    # Déconnexion silencieuse du client
                    break

                message = donnees.decode(ENCODAGE).strip()

                # Commande de sortie
                if message == "/quit":
                    break

                if message:
                    # Diffusion à tous les autres clients, préfixée par le pseudo
                    self.diffuser(f"{pseudo}: {message}", expediteur=client)
                    logging.info(f"CHAT MESSAGE : {pseudo}: {message}")

        except Exception as e:
            logging.error(f"CHAT SERVEUR : erreur avec {adresse} ({e})")
        finally:
            self.retirer_client(client, pseudo)

    def diffuser(self, message, expediteur):
        """Envoie un message à tous les clients connectés, sauf à l'expéditeur lui-même.

        Si expediteur vaut None (message système), le message va à tout le monde."""
        # Copie de la liste des clients sous verrou pour itérer sans risque
        with self.verrou:
            destinataires = list(self.clients.keys())

        for client in destinataires:
            if client is expediteur:
                continue
            try:
                client.send(message.encode(ENCODAGE))
            except Exception:
                # Client injoignable : il sera nettoyé par son propre thread
                pass

    def envoyer_liste_membres(self):
        """Informe tout le monde des membres actuellement connectés."""
        with self.verrou:
            pseudos = list(self.clients.values())
        self.diffuser(f"[Membres connectés : {', '.join(pseudos)}]", expediteur=None)

    def retirer_client(self, client, pseudo):
        """Retire proprement un client déconnecté et prévient les autres."""
        with self.verrou:
            if client in self.clients:
                del self.clients[client]

        try:
            client.close()
        except Exception:
            pass

        if pseudo:
            logging.info(f"CHAT SERVEUR : '{pseudo}' déconnecté.")
            self.diffuser(f"*** {pseudo} a quitté la discussion ***", expediteur=None)


if __name__ == "__main__":
    # Le serveur s'exécute en dehors de main.py : il configure donc son propre logging.
    logging.basicConfig(
        filename="operations.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    ServeurChat().demarrer()
