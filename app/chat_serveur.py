import socket
import threading
import logging
import os

from exceptions_reseau import PseudoInvalideError

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

        # Timeout sur le socket d'écoute : accept() rend la main périodiquement,
        # ce qui permet à Python de traiter le Ctrl+C (KeyboardInterrupt), y compris
        # sous Windows où un accept() bloquant n'est pas interrompu par le signal.
        self.socket_serveur.settimeout(1.0)

        try:
            while True:
                # Attente d'un nouveau client, avec réveil périodique pour le Ctrl+C
                try:
                    client, adresse = self.socket_serveur.accept()
                except socket.timeout:
                    continue

                # Le socket accepté hérite du timeout du serveur : on le repasse en
                # mode bloquant pour la réception normale des messages du client.
                client.settimeout(None)

                # Refus si le nombre maximum de clients est déjà atteint
                with self.verrou:
                    nb_clients = len(self.clients)
                if nb_clients >= MAX_CLIENTS:
                    # On consomme d'abord le pseudo déjà envoyé par le client : fermer
                    # la socket en laissant des données non lues provoque un RST (sous
                    # Windows notamment), et le client ne verrait jamais ce message.
                    try:
                        client.settimeout(1.0)
                        client.recv(1024)
                    except OSError:
                        pass
                    try:
                        client.send("Serveur plein, réessayez plus tard.".encode(ENCODAGE))
                    except OSError:
                        pass
                    client.close()
                    logging.warning(f"CHAT SERVEUR : connexion refusée (serveur plein) {adresse}")
                    continue

                # Un thread dédié par client pour gérer ses messages en parallèle
                thread = threading.Thread(target=self.gerer_client, args=(client, adresse))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")
            logging.info("CHAT SERVEUR : arrêté par l'administrateur.")
        except OSError as e:
            # Erreur bas niveau sur le socket d'écoute : on s'arrête proprement
            # (au lieu de laisser remonter une trace) ; le finally ferme le socket.
            logging.error(f"CHAT SERVEUR : erreur socket, arrêt du serveur ({e})")
            print(f"\nErreur réseau du serveur, arrêt : {e}")
        finally:
            self.socket_serveur.close()

    def gerer_client(self, client, adresse):
        """Gère un client : réception du pseudo puis boucle de réception des messages."""
        pseudo = None
        enregistre = False  # True une fois le client réellement ajouté à la liste
        try:
            # Le tout premier message envoyé par le client est son pseudo
            pseudo_recu = client.recv(1024).decode(ENCODAGE).strip()
            if not pseudo_recu:
                # Pseudo vide : on lève une exception explicite (refus de connexion)
                raise PseudoInvalideError(f"Pseudo vide reçu depuis {adresse}, connexion refusée.")

            # Vérification d'unicité ET réservation du pseudo dans le MÊME verrou,
            # pour éviter que deux clients simultanés obtiennent le même pseudo.
            with self.verrou:
                pseudo_deja_pris = pseudo_recu in self.clients.values()
                if not pseudo_deja_pris:
                    self.clients[client] = pseudo_recu
                    enregistre = True

            if pseudo_deja_pris:
                # Pseudo en doublon : on prévient le client puis on refuse la connexion
                try:
                    client.send(
                        f"Pseudo « {pseudo_recu} » déjà utilisé, choisissez-en un autre.".encode(ENCODAGE)
                    )
                except Exception:
                    pass
                raise PseudoInvalideError(
                    f"Pseudo « {pseudo_recu} » déjà connecté : connexion de {adresse} refusée."
                )

            pseudo = pseudo_recu
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
                    # Diffusion à TOUS les clients (expéditeur inclus) au format
                    # « [ pseudo ] : message ». Chaque client colore le pseudo en bleu
                    # et aligne ses propres messages à droite, ceux des autres à gauche.
                    self.diffuser(f"[ {pseudo} ] : {message}", expediteur=None)
                    logging.info(f"CHAT MESSAGE : {pseudo}: {message}")

        except PseudoInvalideError as e:
            # Cas fonctionnel attendu : on journalise en avertissement, sans trace d'erreur
            logging.warning(f"CHAT SERVEUR : {e}")
        except Exception as e:
            logging.error(f"CHAT SERVEUR : erreur avec {adresse} ({e})")
        finally:
            # On n'annonce le départ que si le client avait bien été enregistré :
            # un pseudo refusé (vide ou en doublon) ne doit pas déclencher de message
            # « a quitté » ni supprimer le client légitime qui portait ce pseudo.
            self.retirer_client(client, pseudo if enregistre else None)

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
