"""Interface graphique (Tkinter) du client de chat interne.

Version graphique de chat_client.py : mêmes protocole et serveur, mais un affichage
en bulles (nos messages à droite en bleu, ceux des autres à gauche), un panneau des
membres connectés et un champ de saisie. Aucune dépendance externe : Tkinter est
fourni avec Python.

Lancement direct :
    python chat_client_gui.py [pseudo] [ip_serveur]
Le port et l'hôte par défaut proviennent des mêmes variables d'environnement que le
client console (CHAT_HOST, CHAT_PORT), pour rester cohérent avec le reste du projet.
"""

import os
import sys
import queue
import socket
import threading

import tkinter as tk
from tkinter import ttk, font as tkfont

# Réutilise la configuration réseau du client console (hôte/port/encodage par défaut)
from chat_client import HOTE, PORT, ENCODAGE

# --- Palette (thème clair, moderne) --------------------------------------------
FOND = "#f0f2f5"           # fond général
FOND_ENTETE = "#1e88e5"    # bandeau supérieur (bleu)
TEXTE_ENTETE = "#ffffff"
BULLE_MOI = "#1e88e5"      # nos messages (bleu, texte blanc)
TEXTE_MOI = "#ffffff"
BULLE_AUTRE = "#ffffff"    # messages des autres (blanc, texte foncé)
TEXTE_AUTRE = "#1c1e21"
PSEUDO_AUTRE = "#1e88e5"   # pseudo de l'expéditeur (bleu)
TEXTE_SYSTEME = "#65676b"  # messages système (gris)
FOND_PANNEAU = "#ffffff"


def _analyser_message(brut, mon_pseudo):
    """Interprète un message reçu du serveur.

    Retourne un tuple (type, donnees) :
      - ("chat", (pseudo, texte, est_moi)) pour un message « [ pseudo ] : texte »
      - ("membres", [pseudo, ...])         pour la liste des membres connectés
      - ("systeme", texte)                 pour tout autre message (arrivée/départ...)"""
    sep = " ] : "
    if brut.startswith("[ ") and sep in brut:
        i = brut.index(sep)
        pseudo = brut[2:i]
        texte = brut[i + len(sep):]
        return "chat", (pseudo, texte, pseudo == mon_pseudo)

    prefixe = "[Membres connectés : "
    if brut.startswith(prefixe) and brut.endswith("]"):
        contenu = brut[len(prefixe):-1].strip()
        membres = [m.strip() for m in contenu.split(",") if m.strip()] if contenu else []
        return "membres", membres

    return "systeme", brut


class ZoneDefilante(ttk.Frame):
    """Conteneur vertical défilant (Canvas + Frame interne) pour empiler les bulles."""

    def __init__(self, parent, fond):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=fond, highlightthickness=0)
        self.barre = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.barre.set)

        self.barre.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Frame interne qui contiendra les bulles
        self.contenu = tk.Frame(self.canvas, bg=fond)
        self.fenetre = self.canvas.create_window((0, 0), window=self.contenu, anchor="nw")

        self.contenu.bind("<Configure>", self._maj_zone_defilement)
        self.canvas.bind("<Configure>", self._ajuster_largeur)
        # Molette de la souris (Windows / macOS)
        self.canvas.bind_all("<MouseWheel>", self._molette)

    def _maj_zone_defilement(self, _evt):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _ajuster_largeur(self, evt):
        # Le contenu occupe toute la largeur visible du canvas
        self.canvas.itemconfigure(self.fenetre, width=evt.width)

    def _molette(self, evt):
        self.canvas.yview_scroll(int(-evt.delta / 120), "units")

    def defiler_en_bas(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)


class FenetreClient(tk.Tk):
    """Fenêtre principale du client : écran de connexion puis écran de discussion."""

    def __init__(self, pseudo="", hote=HOTE, port=PORT):
        super().__init__()
        self.title("Chat interne — Client")
        self.geometry("760x560")
        self.minsize(560, 420)
        self.configure(bg=FOND)

        self.pseudo = pseudo
        self.hote = hote
        self.port = port

        self.socket = None
        self.actif = False
        self._apres_id = None  # identifiant du rappel after() en attente
        # File thread-safe : le thread de réception y dépose les évènements,
        # la boucle Tkinter les consomme via after() (Tkinter n'est pas thread-safe).
        self.file = queue.Queue()

        self.police = tkfont.nametofont("TkDefaultFont")
        self.police.configure(size=10)

        self._construire_connexion()
        self.protocol("WM_DELETE_WINDOW", self._fermer)

    # -- Écran de connexion -----------------------------------------------------
    def _construire_connexion(self):
        self.cadre_connexion = tk.Frame(self, bg=FOND)
        self.cadre_connexion.pack(fill="both", expand=True)

        carte = tk.Frame(self.cadre_connexion, bg=FOND_PANNEAU, padx=30, pady=30)
        carte.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(carte, text="Chat interne", bg=FOND_PANNEAU, fg=FOND_ENTETE,
                 font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 4))
        tk.Label(carte, text="Rejoindre la discussion", bg=FOND_PANNEAU, fg=TEXTE_SYSTEME,
                 font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, pady=(0, 20))

        tk.Label(carte, text="Pseudo", bg=FOND_PANNEAU, anchor="w").grid(row=2, column=0, sticky="w")
        self.champ_pseudo = ttk.Entry(carte, width=28)
        self.champ_pseudo.grid(row=2, column=1, pady=5, padx=(10, 0))
        self.champ_pseudo.insert(0, self.pseudo)

        tk.Label(carte, text="IP du serveur", bg=FOND_PANNEAU, anchor="w").grid(row=3, column=0, sticky="w")
        self.champ_hote = ttk.Entry(carte, width=28)
        self.champ_hote.grid(row=3, column=1, pady=5, padx=(10, 0))
        self.champ_hote.insert(0, self.hote)

        tk.Label(carte, text="Port", bg=FOND_PANNEAU, anchor="w").grid(row=4, column=0, sticky="w")
        self.champ_port = ttk.Entry(carte, width=28)
        self.champ_port.grid(row=4, column=1, pady=5, padx=(10, 0))
        self.champ_port.insert(0, str(self.port))

        self.etat_connexion = tk.Label(carte, text="", bg=FOND_PANNEAU, fg="#d32f2f",
                                       font=("Segoe UI", 9))
        self.etat_connexion.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        self.bouton_connexion = ttk.Button(carte, text="Se connecter", command=self._connecter)
        self.bouton_connexion.grid(row=6, column=0, columnspan=2, pady=(15, 0), sticky="ew")

        self.champ_pseudo.focus_set()
        self.bind("<Return>", lambda _e: self._connecter())

    def _connecter(self):
        pseudo = self.champ_pseudo.get().strip()
        hote = self.champ_hote.get().strip() or HOTE
        port_txt = self.champ_port.get().strip()

        if not pseudo:
            self.etat_connexion.config(text="Le pseudo ne peut pas être vide.")
            return
        try:
            port = int(port_txt)
        except ValueError:
            self.etat_connexion.config(text="Le port doit être un nombre.")
            return

        self.bouton_connexion.config(state="disabled")
        self.etat_connexion.config(text="Connexion en cours...")
        self.update_idletasks()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((hote, port))
            sock.settimeout(None)
            # Le premier message envoyé est le pseudo (protocole attendu par le serveur)
            sock.send(pseudo.encode(ENCODAGE))
        except Exception as e:
            self.etat_connexion.config(text=f"Connexion impossible : {e}")
            self.bouton_connexion.config(state="normal")
            return

        self.socket = sock
        self.pseudo = pseudo
        self.hote = hote
        self.port = port
        self.actif = True

        self.unbind("<Return>")
        self.cadre_connexion.destroy()
        self._construire_discussion()

        # Thread de réception + boucle de dépilement des évènements
        threading.Thread(target=self._boucle_reception, daemon=True).start()
        self._apres_id = self.after(80, self._traiter_file)

    # -- Écran de discussion ----------------------------------------------------
    def _construire_discussion(self):
        # Bandeau supérieur
        entete = tk.Frame(self, bg=FOND_ENTETE, height=54)
        entete.pack(fill="x")
        entete.pack_propagate(False)
        tk.Label(entete, text="  Chat interne", bg=FOND_ENTETE, fg=TEXTE_ENTETE,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=8)
        tk.Label(entete, text=f"Connecté : {self.pseudo}  •  {self.hote}:{self.port}  ",
                 bg=FOND_ENTETE, fg=TEXTE_ENTETE, font=("Segoe UI", 9)).pack(side="right")

        # Corps : zone de messages (gauche) + panneau membres (droite)
        corps = tk.Frame(self, bg=FOND)
        corps.pack(fill="both", expand=True)

        self.zone = ZoneDefilante(corps, FOND)
        self.zone.pack(side="left", fill="both", expand=True)

        panneau = tk.Frame(corps, bg=FOND_PANNEAU, width=170)
        panneau.pack(side="right", fill="y")
        panneau.pack_propagate(False)
        tk.Label(panneau, text="Membres connectés", bg=FOND_PANNEAU, fg=TEXTE_AUTRE,
                 font=("Segoe UI", 10, "bold")).pack(pady=(12, 6), padx=10, anchor="w")
        self.liste_membres = tk.Listbox(panneau, borderwidth=0, highlightthickness=0,
                                        activestyle="none", fg=TEXTE_AUTRE, bg=FOND_PANNEAU,
                                        font=("Segoe UI", 10))
        self.liste_membres.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Barre de saisie
        bas = tk.Frame(self, bg=FOND, pady=8, padx=8)
        bas.pack(fill="x")
        self.champ_saisie = ttk.Entry(bas, font=("Segoe UI", 11))
        self.champ_saisie.pack(side="left", fill="x", expand=True, ipady=4)
        self.champ_saisie.bind("<Return>", lambda _e: self._envoyer())
        ttk.Button(bas, text="Envoyer", command=self._envoyer).pack(side="left", padx=(8, 0))
        self.champ_saisie.focus_set()

    def _ajouter_bulle(self, type_msg, donnees):
        """Ajoute une bulle (message chat) ou une ligne système dans la zone."""
        ligne = tk.Frame(self.zone.contenu, bg=FOND)
        ligne.pack(fill="x", padx=10, pady=3)

        if type_msg == "systeme":
            tk.Label(ligne, text=donnees, bg=FOND, fg=TEXTE_SYSTEME,
                     font=("Segoe UI", 8, "italic")).pack()
            self.zone.defiler_en_bas()
            return

        pseudo, texte, est_moi = donnees
        cote = "right" if est_moi else "left"
        fond_bulle = BULLE_MOI if est_moi else BULLE_AUTRE
        couleur_txt = TEXTE_MOI if est_moi else TEXTE_AUTRE

        bulle = tk.Frame(ligne, bg=fond_bulle)
        bulle.pack(side=cote, anchor="e" if est_moi else "w")

        # Pseudo de l'expéditeur au-dessus (uniquement pour les autres)
        if not est_moi:
            tk.Label(bulle, text=pseudo, bg=fond_bulle, fg=PSEUDO_AUTRE,
                     font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=10, pady=(5, 0))

        tk.Label(bulle, text=texte, bg=fond_bulle, fg=couleur_txt, justify="left",
                 wraplength=380, font=("Segoe UI", 10), anchor="w").pack(
            fill="x", padx=10, pady=(2 if not est_moi else 6, 6))

        self.zone.defiler_en_bas()

    def _maj_membres(self, membres):
        self.liste_membres.delete(0, tk.END)
        for m in membres:
            etiquette = f"• {m}" + ("  (moi)" if m == self.pseudo else "")
            self.liste_membres.insert(tk.END, etiquette)

    # -- Réseau -----------------------------------------------------------------
    def _boucle_reception(self):
        """Thread de fond : lit le socket et dépose les évènements dans la file.

        Les messages sont délimités par '\\n' côté serveur ; on accumule dans un
        tampon et on ne dépile que les messages complets (un recv() peut en
        contenir plusieurs, ou couper un message en deux)."""
        tampon = ""
        while self.actif:
            try:
                donnees = self.socket.recv(1024)
            except Exception:
                self.file.put(("perte", None))
                break
            if not donnees:
                self.file.put(("perte", None))
                break
            tampon += donnees.decode(ENCODAGE)
            while "\n" in tampon:
                ligne, tampon = tampon.split("\n", 1)
                if ligne:
                    self.file.put(("brut", ligne))

    def _traiter_file(self):
        """Consomme les évènements réseau côté Tkinter (thread principal)."""
        try:
            while True:
                genre, charge = self.file.get_nowait()
                if genre == "perte":
                    self.actif = False
                    self._ajouter_bulle("systeme", "Connexion au serveur perdue.")
                    self.champ_saisie.config(state="disabled")
                elif genre == "brut":
                    type_msg, donnees = _analyser_message(charge, self.pseudo)
                    if type_msg == "membres":
                        self._maj_membres(donnees)
                    else:
                        self._ajouter_bulle(type_msg, donnees)
        except queue.Empty:
            pass
        if self.actif:
            self._apres_id = self.after(80, self._traiter_file)

    def _envoyer(self):
        message = self.champ_saisie.get().strip()
        if not message or not self.actif:
            return
        try:
            self.socket.send(message.encode(ENCODAGE))
        except Exception:
            self.actif = False
            self._ajouter_bulle("systeme", "Envoi impossible, connexion fermée.")
            return
        self.champ_saisie.delete(0, tk.END)
        # Le serveur nous renverra le message au format « [ pseudo ] : ... » ;
        # il s'affichera alors à droite. Pas d'écho local pour éviter les doublons.

    def _fermer(self):
        self.actif = False
        if self._apres_id is not None:
            self.after_cancel(self._apres_id)
        if self.socket:
            try:
                self.socket.send("/quit".encode(ENCODAGE))
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
        self.destroy()


def lancer(pseudo="", hote=HOTE, port=PORT):
    FenetreClient(pseudo=pseudo, hote=hote, port=port).mainloop()


if __name__ == "__main__":
    # Arguments optionnels : pseudo puis IP serveur (comme le client console)
    pseudo_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    hote_arg = sys.argv[2] if len(sys.argv) > 2 else os.getenv("CHAT_HOST", HOTE)
    lancer(pseudo=pseudo_arg, hote=hote_arg, port=PORT)
