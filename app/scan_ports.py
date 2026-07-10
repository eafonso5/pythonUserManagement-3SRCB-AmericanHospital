import socket
import time
import logging
from concurrent.futures import ThreadPoolExecutor

# Logger du module, rattaché à la configuration définie dans main.py (operations.log)
logger = logging.getLogger(__name__)

# Cible par défaut : la machine locale (scan autorisé sans risque légal)
HOTE_DEFAUT = "127.0.0.1"

# Quelques ports connus pour enrichir l'affichage des résultats
SERVICES_CONNUS = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
    445: "SMB", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    2121: "FTP (serveur de test)", 5050: "Chat interne",
}


def nom_service(port):
    """Retourne le nom du service associé à un port, ou 'inconnu'."""
    return SERVICES_CONNUS.get(port, "inconnu")


def scanner_un_port(hote, port, timeout=0.5):
    """Teste un port TCP unique. Retourne True si le port est ouvert, False sinon.

    On utilise connect_ex() qui renvoie 0 en cas de succès (port ouvert)
    au lieu de lever une exception, ce qui simplifie le scan de masse."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            resultat = sock.connect_ex((hote, port))
            return resultat == 0
    except Exception as e:
        # Erreur de résolution, hôte injoignable, etc. : le port est considéré fermé
        logger.error(f"SCAN PORT : erreur sur {hote}:{port} ({e})")
        return False


def scanner_plage_sequentiel(hote, port_debut, port_fin, timeout=0.5):
    """Scanne une plage de ports SANS thread (un port après l'autre).

    Retourne un tuple (liste_ports_ouverts, duree_en_secondes)."""
    debut = time.perf_counter()
    ports_ouverts = []

    for port in range(port_debut, port_fin + 1):
        if scanner_un_port(hote, port, timeout):
            ports_ouverts.append(port)

    duree = time.perf_counter() - debut
    logger.info(
        f"SCAN PORTS SÉQUENTIEL : {hote} [{port_debut}-{port_fin}] -> "
        f"{len(ports_ouverts)} ouvert(s) {ports_ouverts} en {duree:.3f}s"
    )
    return ports_ouverts, duree


def scanner_plage_threads(hote, port_debut, port_fin, timeout=0.5, max_workers=100):
    """Scanne une plage de ports AVEC threads (ThreadPoolExecutor, bibliothèque standard).

    Retourne un tuple (liste_ports_ouverts, duree_en_secondes)."""
    debut = time.perf_counter()
    ports = range(port_debut, port_fin + 1)
    ports_ouverts = []

    # Chaque port est testé dans un thread du pool ; on borne le nombre de threads
    # pour rester raisonnable même sur une très grande plage.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # On associe chaque futur résultat à son numéro de port
        resultats = {port: executor.submit(scanner_un_port, hote, port, timeout)
                     for port in ports}

        for port, futur in resultats.items():
            if futur.result():
                ports_ouverts.append(port)

    ports_ouverts.sort()
    duree = time.perf_counter() - debut
    logger.info(
        f"SCAN PORTS THREADS : {hote} [{port_debut}-{port_fin}] -> "
        f"{len(ports_ouverts)} ouvert(s) {ports_ouverts} en {duree:.3f}s"
    )
    return ports_ouverts, duree


def scanner_tous_les_ports(hote, timeout=0.5, max_workers=500):
    """Scanne la totalité des ports (1 à 65535) en parallèle via les threads."""
    logger.info(f"SCAN COMPLET DÉMARRÉ : {hote} (1-65535)")
    return scanner_plage_threads(hote, 1, 65535, timeout, max_workers)


def comparer_performances(hote, port_debut, port_fin, timeout=0.5):
    """Compare le temps d'exécution séquentiel vs threads sur la même plage.

    Répond à la consigne du sujet : mesurer le temps sans thread et avec threads.
    Retourne un dictionnaire avec les deux durées et le gain."""
    ports_seq, duree_seq = scanner_plage_sequentiel(hote, port_debut, port_fin, timeout)
    ports_thr, duree_thr = scanner_plage_threads(hote, port_debut, port_fin, timeout)

    # Calcul du gain (évite la division par zéro sur les scans très rapides)
    gain = (duree_seq / duree_thr) if duree_thr > 0 else 0.0

    logger.info(
        f"COMPARAISON PORTS : {hote} [{port_debut}-{port_fin}] -> "
        f"séquentiel={duree_seq:.3f}s, threads={duree_thr:.3f}s, gain x{gain:.1f}"
    )
    return {
        "ports_ouverts": ports_thr,
        "duree_sequentiel": duree_seq,
        "duree_threads": duree_thr,
        "gain": gain,
    }


# ---------------------------------------------------------------------------
# Fonctions interactives appelées depuis le menu (saisie + affichage)
# ---------------------------------------------------------------------------

def _avertissement():
    """Affiche le rappel légal du sujet avant tout scan."""
    print("\n⚠ Rappel : un scan de ports n'est autorisé que sur un réseau/une machine")
    print("  dont vous avez la permission explicite (par défaut : 127.0.0.1).")


def _demander_hote():
    """Demande l'hôte à scanner, avec 127.0.0.1 par défaut."""
    hote = input(f"Hôte à scanner [{HOTE_DEFAUT}] : ").strip()
    return hote if hote else HOTE_DEFAUT


def _demander_entier(message, defaut):
    """Demande un entier avec une valeur par défaut si la saisie est vide/invalide."""
    valeur = input(f"{message} [{defaut}] : ").strip()
    if not valeur:
        return defaut
    try:
        return int(valeur)
    except ValueError:
        print(f"Valeur invalide, utilisation de {defaut}.")
        return defaut


def _afficher_ports_ouverts(ports_ouverts):
    """Affiche joliment la liste des ports ouverts trouvés."""
    if not ports_ouverts:
        print("\nAucun port ouvert détecté.")
        return
    print(f"\n{len(ports_ouverts)} port(s) ouvert(s) :")
    print("-" * 40)
    print(f"{'Port':<10} | Service")
    print("-" * 40)
    for port in ports_ouverts:
        print(f"{port:<10} | {nom_service(port)}")
    print("-" * 40)


def action_scan_port_unique():
    """Scan d'un seul port choisi par l'utilisateur."""
    print("\n--- SCAN D'UN PORT UNIQUE ---")
    _avertissement()
    hote = _demander_hote()
    port = _demander_entier("Numéro du port", 80)

    ouvert = scanner_un_port(hote, port)
    if ouvert:
        print(f"\n✓ Le port {port} ({nom_service(port)}) est OUVERT sur {hote}.")
    else:
        print(f"\n✗ Le port {port} est fermé ou filtré sur {hote}.")


def action_scan_plage():
    """Scan d'une plage de ports (avec threads)."""
    print("\n--- SCAN D'UNE PLAGE DE PORTS ---")
    _avertissement()
    hote = _demander_hote()
    port_debut = _demander_entier("Port de début", 1)
    port_fin = _demander_entier("Port de fin", 1024)

    if port_debut > port_fin:
        print("Erreur : le port de début doit être inférieur au port de fin.")
        return

    print(f"\nScan de {hote} sur les ports {port_debut} à {port_fin} en cours...")
    ports_ouverts, duree = scanner_plage_threads(hote, port_debut, port_fin)
    _afficher_ports_ouverts(ports_ouverts)
    print(f"\nTemps d'exécution : {duree:.3f} seconde(s).")


def action_scan_tous():
    """Scan de la totalité des ports (1-65535)."""
    print("\n--- SCAN DE TOUS LES PORTS (1-65535) ---")
    _avertissement()
    hote = _demander_hote()

    confirm = input(f"\nScanner les 65535 ports de {hote} ? Cela peut être long (oui/non) : ").strip().lower()
    if confirm != "oui":
        print("Scan annulé.")
        return

    print(f"\nScan complet de {hote} en cours...")
    ports_ouverts, duree = scanner_tous_les_ports(hote)
    _afficher_ports_ouverts(ports_ouverts)
    print(f"\nTemps d'exécution : {duree:.3f} seconde(s).")


def action_comparer_performances():
    """Compare les performances séquentiel vs threads sur une plage."""
    print("\n--- COMPARAISON SÉQUENTIEL vs THREADS ---")
    _avertissement()
    print("\nAstuce : le scan séquentiel teste les ports un par un, il est donc lent")
    print("sur une grande plage. Une petite plage suffit pour observer le gain des threads.")
    hote = _demander_hote()
    port_debut = _demander_entier("Port de début", 1)
    port_fin = _demander_entier("Port de fin", 100)

    if port_debut > port_fin:
        print("Erreur : le port de début doit être inférieur au port de fin.")
        return

    print(f"\nAnalyse comparative sur {hote} [{port_debut}-{port_fin}]...")
    print("(1) Scan séquentiel (sans thread)...")
    print("(2) Scan parallèle (avec threads)...")
    resultat = comparer_performances(hote, port_debut, port_fin)

    _afficher_ports_ouverts(resultat["ports_ouverts"])
    print("\n--- RÉSULTATS ---")
    print(f"Séquentiel (sans thread) : {resultat['duree_sequentiel']:.3f} s")
    print(f"Parallèle  (avec threads) : {resultat['duree_threads']:.3f} s")
    print(f"Gain de performance       : x{resultat['gain']:.1f} plus rapide")
