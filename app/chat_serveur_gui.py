"""Interface graphique (Tkinter) du serveur de chat interne.

Version graphique de chat_serveur.py : réutilise la classe ServeurChat (via son
callback `notifier`) et affiche en temps réel l'état du serveur, les membres
connectés et un journal coloré des arrivées / départs / messages.

Le serveur réseau tourne dans un thread de fond ; les évènements remontent par une
file thread-safe, consommée par la boucle Tkinter (Tkinter n'étant pas thread-safe).

Lancement direct :
    python chat_serveur_gui.py
L'hôte/port par défaut proviennent des mêmes variables d'environnement que le
serveur console (CHAT_HOST, CHAT_PORT).
"""

import os
import queue
import logging
import threading
import time

import tkinter as tk
from tkinter import ttk, font as tkfont

from chat_serveur import ServeurChat, HOTE, PORT, MAX_CLIENTS

# --- Palette -------------------------------------------------------------------
FOND = "#0f1620"           # fond général (sombre, look « console »)
FOND_ENTETE = "#111c2e"
TEXTE_ENTETE = "#e8eef7"
FOND_PANNEAU = "#16202e"
FOND_JOURNAL = "#0b1017"
TEXTE = "#c9d4e3"
VERT = "#4caf50"           # connexions
ROUGE = "#ef5350"          # déconnexions / erreurs
BLEU = "#42a5f5"           # démarrage / infos
GRIS = "#8a97a8"           # messages / horodatage
ORANGE = "#ffa726"         # refus (serveur plein)


class FenetreServeur(tk.Tk):
    """Fenêtre de pilotage du serveur de chat."""

    def __init__(self, hote=HOTE, port=PORT):
        super().__init__()
        self.title("Chat interne — Serveur")
        self.geometry("720x520")
        self.minsize(560, 400)
        self.configure(bg=FOND)

        self.serveur = None
        self.thread = None
        self.en_cours = False
        self._apres_id = None  # identifiant du rappel after() en attente
        # File thread-safe alimentée par le callback notifier (threads serveur)
        self.file = queue.Queue()

        tkfont.nametofont("TkDefaultFont").configure(size=10)

        self._construire(hote, port)
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        self._apres_id = self.after(100, self._traiter_file)

    def _construire(self, hote, port):
        # Bandeau supérieur avec état
        entete = tk.Frame(self, bg=FOND_ENTETE, height=56)
        entete.pack(fill="x")
        entete.pack_propagate(False)
        tk.Label(entete, text="  Serveur de chat", bg=FOND_ENTETE, fg=TEXTE_ENTETE,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=8)
        self.etiquette_etat = tk.Label(entete, text="● Arrêté  ", bg=FOND_ENTETE, fg=ROUGE,
                                       font=("Segoe UI", 11, "bold"))
        self.etiquette_etat.pack(side="right")

        # Barre de configuration + contrôles
        barre = tk.Frame(self, bg=FOND, pady=8, padx=10)
        barre.pack(fill="x")
        tk.Label(barre, text="Hôte", bg=FOND, fg=TEXTE).pack(side="left")
        self.champ_hote = ttk.Entry(barre, width=16)
        self.champ_hote.pack(side="left", padx=(4, 12))
        self.champ_hote.insert(0, hote)
        tk.Label(barre, text="Port", bg=FOND, fg=TEXTE).pack(side="left")
        self.champ_port = ttk.Entry(barre, width=8)
        self.champ_port.pack(side="left", padx=(4, 12))
        self.champ_port.insert(0, str(port))

        self.bouton_demarrer = ttk.Button(barre, text="Démarrer", command=self._demarrer)
        self.bouton_demarrer.pack(side="left", padx=4)
        self.bouton_arreter = ttk.Button(barre, text="Arrêter", command=self._arreter,
                                         state="disabled")
        self.bouton_arreter.pack(side="left", padx=4)

        # Corps : journal (gauche) + membres (droite)
        corps = tk.Frame(self, bg=FOND)
        corps.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cadre_journal = tk.Frame(corps, bg=FOND)
        cadre_journal.pack(side="left", fill="both", expand=True)
        barre_defil = ttk.Scrollbar(cadre_journal)
        barre_defil.pack(side="right", fill="y")
        self.journal = tk.Text(cadre_journal, bg=FOND_JOURNAL, fg=TEXTE, borderwidth=0,
                               highlightthickness=0, wrap="word", state="disabled",
                               font=("Consolas", 10), yscrollcommand=barre_defil.set)
        self.journal.pack(side="left", fill="both", expand=True)
        barre_defil.config(command=self.journal.yview)
        for nom, couleur in (("vert", VERT), ("rouge", ROUGE), ("bleu", BLEU),
                             ("gris", GRIS), ("orange", ORANGE)):
            self.journal.tag_configure(nom, foreground=couleur)

        panneau = tk.Frame(corps, bg=FOND_PANNEAU, width=180)
        panneau.pack(side="right", fill="y", padx=(10, 0))
        panneau.pack_propagate(False)
        self.etiquette_membres = tk.Label(panneau, text=f"Membres  0/{MAX_CLIENTS}",
                                          bg=FOND_PANNEAU, fg=TEXTE_ENTETE,
                                          font=("Segoe UI", 10, "bold"))
        self.etiquette_membres.pack(pady=(12, 6), padx=10, anchor="w")
        self.liste_membres = tk.Listbox(panneau, borderwidth=0, highlightthickness=0,
                                        activestyle="none", fg=TEXTE, bg=FOND_PANNEAU,
                                        font=("Segoe UI", 10))
        self.liste_membres.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # -- Journal ----------------------------------------------------------------
    def _journaliser(self, texte, tag="gris"):
        horodatage = time.strftime("%H:%M:%S")
        self.journal.config(state="normal")
        self.journal.insert("end", f"[{horodatage}] ", "gris")
        self.journal.insert("end", texte + "\n", tag)
        self.journal.see("end")
        self.journal.config(state="disabled")

    def _maj_membres(self, membres):
        self.liste_membres.delete(0, tk.END)
        for m in membres:
            self.liste_membres.insert(tk.END, f"• {m}")
        self.etiquette_membres.config(text=f"Membres  {len(membres)}/{MAX_CLIENTS}")

    # -- Contrôle du serveur ----------------------------------------------------
    def _demarrer(self):
        hote = self.champ_hote.get().strip() or HOTE
        try:
            port = int(self.champ_port.get().strip())
        except ValueError:
            self._journaliser("Port invalide.", "rouge")
            return

        # notifier() est appelé depuis les threads du serveur : il se contente
        # d'empiler l'évènement, tout l'affichage se fait côté Tkinter.
        self.serveur = ServeurChat(hote=hote, port=port, notifier=self._notifier)
        self.thread = threading.Thread(target=self.serveur.demarrer, daemon=True)
        self.en_cours = True
        self.thread.start()

        self.bouton_demarrer.config(state="disabled")
        self.bouton_arreter.config(state="normal")
        self.champ_hote.config(state="disabled")
        self.champ_port.config(state="disabled")

    def _arreter(self):
        if self.serveur:
            self.serveur.arreter()
        self.bouton_arreter.config(state="disabled")
        self._journaliser("Arrêt demandé...", "orange")

    def _notifier(self, evenement, infos):
        """Callback appelé par ServeurChat (threads de fond) : empile l'évènement."""
        self.file.put((evenement, infos))

    def _traiter_file(self):
        """Consomme les évènements du serveur côté Tkinter (thread principal)."""
        try:
            while True:
                evenement, infos = self.file.get_nowait()
                self._appliquer(evenement, infos)
        except queue.Empty:
            pass
        self._apres_id = self.after(100, self._traiter_file)

    def _appliquer(self, evenement, infos):
        if evenement == "demarre":
            self.etiquette_etat.config(text="● En écoute  ", fg=VERT)
            self._journaliser(
                f"Serveur démarré sur {infos['hote']}:{infos['port']} "
                f"(max {infos['max_clients']} clients).", "bleu")
        elif evenement == "connexion":
            self._journaliser(
                f"[+] {infos['pseudo']} connecté depuis {infos['adresse']} "
                f"({infos['nb']}/{MAX_CLIENTS}).", "vert")
            self._maj_membres(infos["membres"])
        elif evenement == "deconnexion":
            self._journaliser(
                f"[-] {infos['pseudo']} déconnecté ({infos['nb']}/{MAX_CLIENTS}).", "rouge")
            self._maj_membres(infos["membres"])
        elif evenement == "message":
            self._journaliser(f"{infos['pseudo']} : {infos['texte']}", "gris")
        elif evenement == "refus":
            self._journaliser(f"Connexion refusée (serveur plein) : {infos['adresse']}.", "orange")
        elif evenement == "erreur":
            self.etiquette_etat.config(text="● Erreur  ", fg=ROUGE)
            self._journaliser(f"Erreur réseau : {infos['message']}", "rouge")
        elif evenement == "arret":
            self.en_cours = False
            self.etiquette_etat.config(text="● Arrêté  ", fg=ROUGE)
            self._journaliser("Serveur arrêté.", "orange")
            self._maj_membres([])
            self.bouton_demarrer.config(state="normal")
            self.bouton_arreter.config(state="disabled")
            self.champ_hote.config(state="normal")
            self.champ_port.config(state="normal")

    def _fermer(self):
        if self.serveur and self.en_cours:
            self.serveur.arreter()
        if self._apres_id is not None:
            self.after_cancel(self._apres_id)
        self.destroy()


def lancer(hote=HOTE, port=PORT):
    FenetreServeur(hote=hote, port=port).mainloop()


if __name__ == "__main__":
    # Le serveur GUI configure son propre logging (comme le serveur console)
    logging.basicConfig(
        filename="operations.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    # Par défaut, on écoute sur toutes les interfaces pour accepter clients locaux/distants
    lancer(hote=os.getenv("CHAT_HOST", "0.0.0.0"), port=PORT)
