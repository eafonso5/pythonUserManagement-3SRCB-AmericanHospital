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


# Couleurs ANSI pour l'affichage
_BLEU = "\033[94m"
_RESET = "\033[0m"


def _formater_reception(msg, mon_pseudo):
    """Prépare l'affichage d'un message reçu du serveur.

    Les messages de chat ont la forme « [ pseudo ] : texte ». Le préfixe
    « [ pseudo ] : » est coloré en bleu. Retourne un tuple :
      (texte_colore, longueur_visible, aligner_a_droite)
    où longueur_visible ignore les codes couleur (invisibles) pour permettre un
    alignement correct. Un message émis par nous-mêmes est aligné à droite ; les
    messages système (arrivée/départ, liste des membres) restent à gauche."""
    sep = " ] : "
    if msg.startswith("[ ") and sep in msg:
        i = msg.index(sep)
        pseudo = msg[2:i]
        texte = msg[i + len(sep):]
        prefixe = f"[ {pseudo} ] :"
        colore = f"{_BLEU}{prefixe}{_RESET} {texte}"
        longueur_visible = len(prefixe) + 1 + len(texte)
        return colore, longueur_visible, (pseudo == mon_pseudo)
    # Message système : affiché tel quel, à gauche
    return msg, len(msg), False


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

        # Notre pseudo (renseigné au démarrage) : sert à reconnaître nos propres
        # messages renvoyés par le serveur, pour les aligner à droite.
        self.pseudo = ""

        # Verrou pour éviter que l'affichage d'un message reçu (thread de réception)
        # ne s'entrelace avec l'effacement de notre saisie clavier.
        self.verrou_affichage = threading.Lock()

        # Tampon de réception : les messages sont délimités par '\n' côté serveur,
        # mais un recv() peut en contenir plusieurs (ou un message tronqué). On
        # accumule ici et on ne traite que les lignes complètes.
        self._tampon = ""

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

                # On accumule puis on traite chaque message complet (délimité par '\n')
                self._tampon += donnees.decode(ENCODAGE)
                while "\n" in self._tampon:
                    ligne, self._tampon = self._tampon.split("\n", 1)
                    if not ligne:
                        continue
                    # Affichage : pseudo en bleu ; à droite si c'est notre message,
                    # à gauche pour les messages des autres et les messages système.
                    colore, longueur, a_droite = _formater_reception(ligne, self.pseudo)
                    with self.verrou_affichage:
                        if a_droite:
                            pad = max(0, _largeur_terminal() - longueur)
                            print(" " * pad + colore)
                        else:
                            print(colore)
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

            # On efface l'écho clavier local de notre saisie (\033[F remonte d'une
            # ligne, \033[2K l'efface). Le message nous sera renvoyé par le serveur
            # au format « [ pseudo ] : ... » et affiché à droite par le thread de
            # réception : on n'a donc qu'une seule ligne, avec le pseudo.
            if message and message != "/quit":
                with self.verrou_affichage:
                    sys.stdout.write("\033[F\033[2K")
                    sys.stdout.flush()

            if message == "/quit":
                self.actif = False
                break

    def demarrer(self, pseudo):
        """Lance le client : connexion, thread de réception, boucle d'envoi."""
        # Nécessaire pour que les couleurs et l'alignement fonctionnent sous Windows
        _activer_ansi_windows()

        # Mémorisé pour reconnaître nos propres messages (affichés à droite)
        self.pseudo = pseudo

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
