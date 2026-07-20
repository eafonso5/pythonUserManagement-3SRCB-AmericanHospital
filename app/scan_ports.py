import socket
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from exceptions_reseau import PlagePortsInvalideError

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
    au lieu de lever une exception, ce qui simplifie le scan de masse.

    getaddrinfo choisit automatiquement la bonne famille d'adresse (AF_INET
    pour l'IPv4, AF_INET6 pour l'IPv6), ce qui rend le scan compatible IPv6
    aussi bien pour une IP littérale (ex : ::1) que pour un nom de machine."""
    try:
        # On récupère la famille/protocole adaptés à l'hôte (IPv4 ou IPv6)
        famille, type_sock, proto, _, adresse = socket.getaddrinfo(
            hote, port, type=socket.SOCK_STREAM
        )[0]
        with socket.socket(famille, type_sock, proto) as sock:
            sock.settimeout(timeout)
            resultat = sock.connect_ex(adresse)
            return resultat == 0
    except Exception as e:
        # Erreur de résolution, hôte injoignable, etc. : le port est considéré fermé
        logger.error(f"SCAN PORT : erreur sur {hote}:{port} ({e})")
        return False


def _valider_plage(port_debut, port_fin):
    """Valide une plage de ports. Lève PlagePortsInvalideError si elle est incorrecte.

    Un port valide est compris entre 1 et 65535 et le début ne peut dépasser la fin."""
    if not (1 <= port_debut <= 65535) or not (1 <= port_fin <= 65535):
        raise PlagePortsInvalideError(
            f"Ports hors limites (autorisé : 1-65535) : {port_debut}-{port_fin}."
        )
    if port_debut > port_fin:
        raise PlagePortsInvalideError(
            f"Le port de début ({port_debut}) est supérieur au port de fin ({port_fin})."
        )


def scanner_plage_sequentiel(hote, port_debut, port_fin, timeout=0.5):
    """Scanne une plage de ports SANS thread (un port après l'autre).

    Retourne un tuple (liste_ports_ouverts, duree_en_secondes).
    Lève PlagePortsInvalideError si la plage est invalide."""
    _valider_plage(port_debut, port_fin)
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


def scanner_plage_threads(hote, port_debut, port_fin, timeout=0.5, max_workers=10000):
    """Scanne une plage de ports AVEC threads (ThreadPoolExecutor, bibliothèque standard).

    Retourne un tuple (liste_ports_ouverts, duree_en_secondes).
    Lève PlagePortsInvalideError si la plage est invalide."""
    _valider_plage(port_debut, port_fin)
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


def scanner_tous_les_ports(hote, timeout=0.5, max_workers=10000):
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
# Scan UDP (le sujet demande de ne pas se limiter au TCP)
# ---------------------------------------------------------------------------

def scanner_un_port_udp(hote, port, timeout=1.0):
    """Teste un port UDP unique. Compatible IPv4 et IPv6 via getaddrinfo.

    UDP est un protocole sans connexion : l'interprétation diffère du TCP.
      - une réponse reçue          -> 'ouvert'
      - une erreur ICMP            -> 'fermé' (port unreachable)
      - aucune réponse (timeout)   -> 'ouvert|filtré' (indéterminé, propre à UDP)
    Retourne l'une de ces chaînes de statut ('erreur' en cas d'échec technique)."""
    try:
        famille, type_sock, proto, _, adresse = socket.getaddrinfo(
            hote, port, type=socket.SOCK_DGRAM
        )[0]
        with socket.socket(famille, type_sock, proto) as sock:
            sock.settimeout(timeout)
            # Datagramme vide : on cherche seulement à provoquer une réaction
            sock.sendto(b"", adresse)
            try:
                sock.recvfrom(1024)
                return "ouvert"          # le service a répondu
            except socket.timeout:
                return "ouvert|filtré"   # silence : impossible de trancher en UDP
            except OSError:
                return "fermé"           # ICMP port unreachable reçu
    except Exception as e:
        logger.error(f"SCAN UDP : erreur sur {hote}:{port} ({e})")
        return "erreur"


def scanner_plage_udp_threads(hote, port_debut, port_fin, timeout=1.0, max_workers=10000):
    """Scanne une plage de ports UDP AVEC threads.

    Retourne (liste de tuples (port, statut) hors 'fermé'/'erreur', duree).
    Lève PlagePortsInvalideError si la plage est invalide."""
    _valider_plage(port_debut, port_fin)
    debut = time.perf_counter()
    ports = range(port_debut, port_fin + 1)
    resultats = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futurs = {port: executor.submit(scanner_un_port_udp, hote, port, timeout)
                  for port in ports}
        for port, futur in futurs.items():
            statut = futur.result()
            # On ignore les ports clairement fermés et les erreurs techniques
            if statut not in ("fermé", "erreur"):
                resultats.append((port, statut))

    resultats.sort()
    duree = time.perf_counter() - debut
    logger.info(
        f"SCAN UDP THREADS : {hote} [{port_debut}-{port_fin}] -> "
        f"{len(resultats)} port(s) non fermé(s) en {duree:.3f}s"
    )
    return resultats, duree


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


def _demander_protocole():
    """Demande le(s) protocole(s) à scanner.

    Retourne une liste : ['tcp'], ['udp'] ou ['tcp', 'udp']."""
    print("\nProtocole à scanner :")
    print("  1. TCP")
    print("  2. UDP")
    print("  3. Les deux (TCP + UDP)")
    choix = input("Votre choix [1] : ").strip()
    if choix == "2":
        return ["udp"]
    if choix == "3":
        return ["tcp", "udp"]
    # Vide, '1' ou saisie invalide : TCP par défaut
    return ["tcp"]


def _afficher_ports_udp(resultats):
    """Affiche la liste des ports UDP non fermés (ouvert / ouvert|filtré)."""
    if not resultats:
        print("Aucun port UDP ouvert/filtré détecté (tous fermés).")
        return
    print(f"{len(resultats)} port(s) UDP non fermé(s) :")
    print("-" * 50)
    print(f"{'Port':<8} | {'Statut':<15} | Service")
    print("-" * 50)
    for port, statut in resultats:
        print(f"{port:<8} | {statut:<15} | {nom_service(port)}")
    print("-" * 50)


def action_scan_port_unique():
    """Scan d'un seul port : choix du port puis du/des protocole(s)."""
    print("\n--- SCAN D'UN PORT UNIQUE ---")
    _avertissement()
    hote = _demander_hote()
    port = _demander_entier("Numéro du port", 80)
    protocoles = _demander_protocole()

    if "tcp" in protocoles:
        debut = time.perf_counter()
        ouvert = scanner_un_port(hote, port)
        duree = time.perf_counter() - debut
        etat = "OUVERT" if ouvert else "fermé ou filtré"
        print(f"\n[TCP] Port {port} ({nom_service(port)}) sur {hote} : {etat}  ({duree:.3f}s)")

    if "udp" in protocoles:
        print("\nNote UDP : l'absence de réponse est ambiguë (ouvert ou filtré).")
        debut = time.perf_counter()
        statut = scanner_un_port_udp(hote, port)
        duree = time.perf_counter() - debut
        print(f"[UDP] Port {port} ({nom_service(port)}) sur {hote} : {statut.upper()}  ({duree:.3f}s)")


def action_scan_plage():
    """Scan d'une plage de ports (threads) : bornes puis protocole(s)."""
    print("\n--- SCAN D'UNE PLAGE DE PORTS ---")
    _avertissement()
    hote = _demander_hote()
    port_debut = _demander_entier("Port de début", 1)
    port_fin = _demander_entier("Port de fin", 1024)
    protocoles = _demander_protocole()

    try:
        if "tcp" in protocoles:
            print(f"\n[TCP] Scan de {hote} [{port_debut}-{port_fin}] en cours...")
            ports_ouverts, duree = scanner_plage_threads(hote, port_debut, port_fin)
            _afficher_ports_ouverts(ports_ouverts)
            print(f"Temps [TCP] : {duree:.3f} seconde(s).")

        if "udp" in protocoles:
            print(f"\n[UDP] Scan de {hote} [{port_debut}-{port_fin}] en cours...")
            print("(UDP : seuls les ports clairement fermés sont écartés)")
            resultats, duree = scanner_plage_udp_threads(hote, port_debut, port_fin)
            _afficher_ports_udp(resultats)
            print(f"Temps [UDP] : {duree:.3f} seconde(s).")
    except PlagePortsInvalideError as e:
        print(f"\nErreur : {e}")
    except KeyboardInterrupt:
        print("\nScan interrompu par l'utilisateur.")


def action_scan_tous():
    """Scan de la totalité des ports (1-65535) : protocole(s) au choix."""
    print("\n--- SCAN DE TOUS LES PORTS (1-65535) ---")
    _avertissement()
    hote = _demander_hote()
    protocoles = _demander_protocole()

    confirm = input(f"\nScanner les 65535 ports de {hote} ? Cela peut être long (oui/non) : ").strip().lower()
    if confirm != "oui":
        print("Scan annulé.")
        return

    try:
        if "tcp" in protocoles:
            print(f"\n[TCP] Scan complet de {hote} en cours...")
            ports_ouverts, duree = scanner_tous_les_ports(hote)
            _afficher_ports_ouverts(ports_ouverts)
            print(f"Temps [TCP] : {duree:.3f} seconde(s).")

        if "udp" in protocoles:
            print(f"\n[UDP] Scan complet de {hote} en cours...")
            resultats, duree = scanner_plage_udp_threads(hote, 1, 65535)
            _afficher_ports_udp(resultats)
            print(f"Temps [UDP] : {duree:.3f} seconde(s).")
    except KeyboardInterrupt:
        print("\nScan interrompu par l'utilisateur.")


def action_comparer_performances():
    """Compare les performances séquentiel vs threads sur une plage."""
    print("\n--- COMPARAISON SÉQUENTIEL vs THREADS ---")
    _avertissement()
    print("\nAstuce : le scan séquentiel teste les ports un par un, il est donc lent")
    print("sur une grande plage. Une petite plage suffit pour observer le gain des threads.")
    hote = _demander_hote()
    port_debut = _demander_entier("Port de début", 1)
    port_fin = _demander_entier("Port de fin", 100)

    print(f"\nAnalyse comparative sur {hote} [{port_debut}-{port_fin}]...")
    print("(1) Scan séquentiel (sans thread)...")
    print("(2) Scan parallèle (avec threads)...")
    try:
        resultat = comparer_performances(hote, port_debut, port_fin)
    except PlagePortsInvalideError as e:
        print(f"\nErreur : {e}")
        return
    except KeyboardInterrupt:
        print("\nScan interrompu par l'utilisateur.")
        return

    _afficher_ports_ouverts(resultat["ports_ouverts"])
    print("\n--- RÉSULTATS ---")
    print(f"Séquentiel (sans thread) : {resultat['duree_sequentiel']:.3f} s")
    print(f"Parallèle  (avec threads) : {resultat['duree_threads']:.3f} s")
    print(f"Gain de performance       : x{resultat['gain']:.1f} plus rapide")
