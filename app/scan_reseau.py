import socket
import subprocess
import platform
import ipaddress
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from exceptions_reseau import ReseauInvalideError

# Logger du module, rattaché à la configuration définie dans main.py (operations.log)
logger = logging.getLogger(__name__)

# Système d'exploitation courant (détecté une seule fois au chargement du module)
_SYSTEME = platform.system().lower()


def _log_dimension_pool(n_taches, max_workers, workers, verbose):
    """(verbose) Affiche le dimensionnement du pool de threads avant un scan réseau."""
    if not verbose:
        return
    print(f"[verbose] {n_taches} hôte(s), max_workers demandé={max_workers} "
          f"-> {workers} thread(s) effectif(s)")
    if workers > 2000:
        print(f"[verbose] ATTENTION : {workers} threads = autant de processus 'ping' "
              f"potentiellement simultanés ; risque de saturation.")


def _log_echec_pool(workers, exc, verbose):
    """(verbose + journal) Signale un échec de création/exécution du pool de threads."""
    msg = f"échec du pool de threads ({workers} workers) : {type(exc).__name__}: {exc}"
    if verbose:
        print(f"[verbose] ÉCHEC -> {msg}")
    logger.error(f"SCAN RÉSEAU : {msg}")


def resoudre_dns(nom):
    """Résout un nom de machine en adresses IP (DNS direct).

    Utilise getaddrinfo qui retourne aussi bien des adresses IPv4 que IPv6.
    Retourne une liste d'adresses (sans doublon), vide en cas d'échec."""
    adresses = []
    try:
        # getaddrinfo renvoie une liste de tuples ; l'adresse est dans sockaddr[0]
        for info in socket.getaddrinfo(nom, None):
            ip = info[4][0]
            if ip not in adresses:
                adresses.append(ip)
        logger.info(f"DNS : {nom} -> {adresses}")
    except Exception as e:
        logger.error(f"DNS : échec de résolution de '{nom}' ({e})")
    return adresses


# Requête NetBIOS « node status » (NBSTAT) pour le nom générique « * ».
# En-tête (12 o) + nom encodé de « * » (0x20 + "CK"+30x"A" + 0x00) + type 0x21 + classe 0x01.
_REQUETE_NBSTAT = (
    b"\xa2\x48\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    b"\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00"
    b"\x00\x21\x00\x01"
)


def _nom_netbios(ip, timeout=1.0):
    """Interroge le nom NetBIOS d'une machine par une requête « node status » UDP
    directe (port 137).

    Très utile sur un LAN où les postes clients n'ont pas d'enregistrement PTR dans
    le DNS (fréquent en Wi-Fi) : la machine répond elle-même son nom. Bien plus
    rapide que « nbtstat -A » (qui sonde toutes les cartes réseau locales) car le
    paquet est routé directement vers la cible. Retourne le nom, ou None."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(_REQUETE_NBSTAT, (str(ip), 137))
            data, _ = sock.recvfrom(2048)
    except Exception:
        # Pas de réponse : hôte non-Windows, NetBIOS désactivé ou filtré. Cas normal.
        return None

    # Réponse : en-tête (12) + nom (34) + type/classe/TTL/rdlength (10) = 56 octets,
    # puis 1 octet indiquant le nombre de noms, puis 18 octets par nom.
    if len(data) < 57:
        return None
    nb_noms = data[56]
    offset = 57
    for _ in range(nb_noms):
        bloc = data[offset:offset + 18]
        if len(bloc) < 18:
            break
        nom = bloc[0:15].decode("ascii", "ignore").strip()
        suffixe = bloc[15]
        flags = int.from_bytes(bloc[16:18], "big")
        est_groupe = bool(flags & 0x8000)
        # Le nom de l'ordinateur = suffixe 0x00, entrée UNIQUE (bit groupe à 0)
        if suffixe == 0x00 and not est_groupe and nom:
            return nom
        offset += 18
    return None


def reverse_dns(ip):
    """Résout une adresse IP en nom de machine.

    Tente d'abord le DNS inverse (PTR) ; en cas d'échec, se rabat sur le nom
    NetBIOS (efficace sur un LAN Windows sans enregistrement PTR).
    Retourne le nom trouvé, ou None si aucune correspondance."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        # Pas d'enregistrement PTR : cas normal sur un LAN. On tente le NetBIOS.
        return _nom_netbios(ip)


def _construire_commande_ping(ip):
    """Construit la commande ping adaptée à l'OS et à la version IP (IPv4/IPv6).

    On envoie un seul paquet avec un court délai d'attente. La détection
    IPv4/IPv6 s'appuie sur le module ipaddress (aucune dépendance externe)."""
    # Détermination de la version d'IP pour ajouter l'option -6 si nécessaire
    option_ipv6 = []
    try:
        if ipaddress.ip_address(ip).version == 6:
            option_ipv6 = ["-6"]
    except ValueError:
        # Ce n'est pas une IP littérale (ex : un nom de machine) : ping résoudra lui-même
        pass

    if _SYSTEME == "windows":
        # -n 2 : deux envois (le 1er paquet vers un hôte jamais contacté est souvent
        # perdu pendant la résolution ARP/ND, ce qui donnait de faux « injoignable »),
        # -w 1000 : timeout par paquet en millisecondes
        return ["ping", "-n", "2", "-w", "1000"] + option_ipv6 + [str(ip)]
    else:
        # -c 2 : deux envois (idem, robustesse au 1er paquet perdu),
        # -W 1 : timeout par paquet en secondes (Linux/Mac)
        return ["ping", "-c", "2", "-W", "1"] + option_ipv6 + [str(ip)]


# Marqueurs présents uniquement dans une VRAIE réponse d'écho ICMP.
# Un écho valide indique soit une durée aller-retour (time/temps), soit le TTL.
# Les réponses « Destination host unreachable » et « Request timed out » n'en
# contiennent aucun. Ces marqueurs couvrent Windows et Linux/Mac, en anglais
# comme en français (IPv4 affiche 'TTL=', l'IPv6 sous Windows affiche 'time<...').
_MARQUEURS_ECHO = ("ttl=", "time<", "time=", "temps<", "temps=")


def ping_hote(ip):
    """Teste si un hôte répond au ping. Retourne True si vivant, False sinon.

    Deux conditions doivent être réunies :
      1. le processus ping se termine avec le code 0, ET
      2. sa sortie contient un des marqueurs d'écho ICMP (cf. _MARQUEURS_ECHO).
    La seconde condition est indispensable sous Windows : ping y renvoie le code 0
    même quand un routeur répond « Destination host unreachable » (sans durée ni TTL),
    ce qui provoquerait de faux positifs sur les IP non attribuées."""
    commande = _construire_commande_ping(ip)
    try:
        resultat = subprocess.run(
            commande,
            capture_output=True,   # on récupère la sortie pour vérifier l'écho ICMP
            text=True,
            errors="ignore",       # évite tout souci d'encodage selon la langue de l'OS
            timeout=5,
        )
        sortie = (resultat.stdout or "").lower()
        echo_valide = any(marqueur in sortie for marqueur in _MARQUEURS_ECHO)
        return resultat.returncode == 0 and echo_valide
    except Exception as e:
        logger.error(f"PING : erreur sur {ip} ({e})")
        return False


def scanner_ip(ip):
    """Scanne une seule IP : ping + résolution DNS inverse.

    Retourne un dictionnaire {ip, vivant, nom}."""
    vivant = ping_hote(ip)
    nom = reverse_dns(ip) if vivant else None
    logger.info(f"SCAN IP : {ip} -> {'vivant' if vivant else 'injoignable'}"
                + (f" ({nom})" if nom else ""))
    return {"ip": ip, "vivant": vivant, "nom": nom}


def _lister_hotes(reseau_cidr):
    """Retourne la liste des IP à scanner à partir d'une notation CIDR.

    ip_network gère indifféremment l'IPv4 et l'IPv6. Pour une IP unique
    (ex : '127.0.0.1'), on la scanne directement.
    Lève ReseauInvalideError si la notation est incorrecte."""
    try:
        reseau = ipaddress.ip_network(reseau_cidr, strict=False)
    except ValueError as e:
        # On transforme l'erreur bas niveau en exception métier explicite et claire
        raise ReseauInvalideError(f"Notation réseau invalide : '{reseau_cidr}' ({e}).") from e

    # .hosts() exclut réseau et broadcast ; s'il n'y a qu'une adresse, on la garde
    hotes = list(reseau.hosts())
    if not hotes:
        hotes = [reseau.network_address]
    return [str(h) for h in hotes]


def scanner_plage_sequentiel(reseau_cidr):
    """Scanne une plage d'adresses SANS thread. Retourne (liste_resultats_vivants, duree).
    Lève ReseauInvalideError si la notation CIDR est invalide."""
    debut = time.perf_counter()
    hotes = _lister_hotes(reseau_cidr)

    vivants = []
    for ip in hotes:
        resultat = scanner_ip(ip)
        if resultat["vivant"]:
            vivants.append(resultat)

    duree = time.perf_counter() - debut
    logger.info(
        f"SCAN RÉSEAU SÉQUENTIEL : {reseau_cidr} ({len(hotes)} hôtes) -> "
        f"{len(vivants)} vivant(s) en {duree:.3f}s"
    )
    return vivants, duree


def scanner_plage_threads(reseau_cidr, max_workers=512, verbose=False):
    """Scanne une plage d'adresses AVEC threads. Retourne (liste_resultats_vivants, duree).
    Lève ReseauInvalideError si la notation CIDR est invalide.

    verbose=True affiche le dimensionnement du pool, une progression régulière et
    signale explicitement un échec de création de threads (max_workers trop élevé),
    utile pour diagnostiquer une saturation sur une grande plage."""
    debut = time.perf_counter()
    hotes = _lister_hotes(reseau_cidr)

    # Inutile d'allouer plus de threads que d'hôtes à pinger
    workers = min(max_workers, len(hotes)) or 1
    _log_dimension_pool(len(hotes), max_workers, workers, verbose)

    vivants = []
    traites = 0
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            if verbose:
                print(f"[verbose] pool créé ({workers} workers), soumission de {len(hotes)} tâche(s)...")
            futures = [executor.submit(scanner_ip, ip) for ip in hotes]
            if verbose:
                print("[verbose] tâches soumises, attente des résultats...")
            for future in as_completed(futures):
                traites += 1
                resultat = future.result()
                if resultat["vivant"]:
                    vivants.append(resultat)
                if verbose and traites % 500 == 0:
                    print(f"[verbose] {traites}/{len(hotes)} traités, {len(vivants)} vivant(s)")
    except (RuntimeError, MemoryError, OSError) as e:
        # Typiquement "can't start new thread" quand max_workers est trop grand
        _log_echec_pool(workers, e, verbose)
        raise

    # Tri des résultats par adresse IP pour un affichage stable
    vivants.sort(key=lambda r: ipaddress.ip_address(r["ip"]))
    duree = time.perf_counter() - debut
    if verbose:
        print(f"[verbose] terminé en {duree:.1f}s, {len(vivants)} vivant(s)")
    logger.info(
        f"SCAN RÉSEAU THREADS : {reseau_cidr} ({len(hotes)} hôtes) -> "
        f"{len(vivants)} vivant(s) en {duree:.3f}s"
    )
    return vivants, duree


def comparer_performances_reseau(reseau_cidr):
    """Compare le temps séquentiel vs threads sur la même plage réseau.

    Répond à la consigne : mesurer le temps sans et avec threads."""
    vivants_seq, duree_seq = scanner_plage_sequentiel(reseau_cidr)
    vivants_thr, duree_thr = scanner_plage_threads(reseau_cidr)

    gain = (duree_seq / duree_thr) if duree_thr > 0 else 0.0
    logger.info(
        f"COMPARAISON RÉSEAU : {reseau_cidr} -> "
        f"séquentiel={duree_seq:.3f}s, threads={duree_thr:.3f}s, gain x{gain:.1f}"
    )
    return {
        "vivants": vivants_thr,
        "duree_sequentiel": duree_seq,
        "duree_threads": duree_thr,
        "gain": gain,
    }


# ---------------------------------------------------------------------------
# Fonctions interactives appelées depuis le menu (saisie + affichage)
# ---------------------------------------------------------------------------

def _avertissement():
    """Affiche le rappel légal du sujet avant tout scan réseau."""
    print("\n⚠ Rappel : un scan réseau n'est autorisé que sur un réseau dont vous avez")
    print("  la permission explicite (par défaut : machine locale / réseau privé).")


def _afficher_vivants(vivants):
    """Affiche la liste des hôtes vivants trouvés."""
    if not vivants:
        print("\nAucun hôte vivant détecté.")
        return
    print(f"\n{len(vivants)} hôte(s) vivant(s) :")
    print("-" * 55)
    print(f"{'Adresse IP':<40} | Nom (reverse DNS)")
    print("-" * 55)
    for hote in vivants:
        nom = hote["nom"] if hote["nom"] else "(inconnu)"
        print(f"{hote['ip']:<40} | {nom}")
    print("-" * 55)


def action_scan_ip():
    """Scan d'une adresse IP unique (ping + reverse DNS)."""
    print("\n--- SCAN D'UNE IP UNIQUE ---")
    _avertissement()
    ip = input("Adresse IP à scanner [127.0.0.1] : ").strip() or "127.0.0.1"

    print(f"\nTest de {ip} en cours...")
    debut = time.perf_counter()
    resultat = scanner_ip(ip)
    duree = time.perf_counter() - debut

    if resultat["vivant"]:
        nom = resultat["nom"] if resultat["nom"] else "(nom inconnu)"
        print(f"\n✓ {ip} répond (vivant). Nom : {nom}")
    else:
        print(f"\n✗ {ip} ne répond pas (injoignable ou ping bloqué).")
    print(f"\nTemps d'exécution : {duree:.3f} seconde(s).")


def action_scan_dns():
    """Résolution DNS d'un nom de machine (IPv4 + IPv6)."""
    print("\n--- SCAN PAR NOM DE MACHINE (DNS) ---")
    nom = input("Nom de machine à résoudre [localhost] : ").strip() or "localhost"

    print(f"\nRésolution DNS de '{nom}' en cours...")
    debut = time.perf_counter()
    adresses = resoudre_dns(nom)
    duree = time.perf_counter() - debut

    if not adresses:
        print(f"\n✗ Impossible de résoudre '{nom}'.")
        print(f"\nTemps d'exécution : {duree:.3f} seconde(s).")
        return

    print(f"\n✓ '{nom}' résolu en {len(adresses)} adresse(s) :")
    for ip in adresses:
        # ip_address permet d'indiquer si c'est de l'IPv4 ou de l'IPv6
        try:
            version = ipaddress.ip_address(ip).version
            print(f"  - {ip}  (IPv{version})")
        except ValueError:
            print(f"  - {ip}")
    print(f"\nTemps d'exécution : {duree:.3f} seconde(s).")


def action_scan_plage():
    """Scan d'une plage d'adresses (avec threads) + reverse DNS des hôtes vivants."""
    print("\n--- SCAN D'UNE PLAGE / D'UN RÉSEAU ---")
    _avertissement()
    print("Exemples : 127.0.0.1/32, 192.168.1.0/24, ::1/128")
    cidr = input("Réseau au format CIDR [127.0.0.1/32] : ").strip() or "127.0.0.1/32"

    try:
        # _lister_hotes valide la notation et lève ReseauInvalideError si besoin
        nb_hotes = len(_lister_hotes(cidr))
        print(f"\nScan de {cidr} ({nb_hotes} hôte(s)) en cours...")
        vivants, duree = scanner_plage_threads(cidr, verbose=True)
    except ReseauInvalideError as e:
        print(f"\nErreur : {e}")
        return
    except KeyboardInterrupt:
        print("\nScan interrompu par l'utilisateur.")
        return

    _afficher_vivants(vivants)
    print(f"\nTemps d'exécution : {duree:.3f} seconde(s).")


def action_comparer_performances():
    """Compare séquentiel vs threads sur une plage réseau."""
    print("\n--- COMPARAISON SÉQUENTIEL vs THREADS (réseau) ---")
    _avertissement()
    print("Exemples : 192.168.1.0/28, 10.0.0.0/29")
    cidr = input("Réseau au format CIDR [127.0.0.1/29] : ").strip() or "127.0.0.1/29"

    try:
        nb_hotes = len(_lister_hotes(cidr))
        print(f"\nAnalyse comparative sur {cidr} ({nb_hotes} hôte(s))...")
        print("(1) Scan séquentiel (sans thread)...")
        print("(2) Scan parallèle (avec threads)...")
        resultat = comparer_performances_reseau(cidr)
    except ReseauInvalideError as e:
        print(f"\nErreur : {e}")
        return
    except KeyboardInterrupt:
        print("\nScan interrompu par l'utilisateur.")
        return

    _afficher_vivants(resultat["vivants"])
    print("\n--- RÉSULTATS ---")
    print(f"Séquentiel (sans thread) : {resultat['duree_sequentiel']:.3f} s")
    print(f"Parallèle  (avec threads) : {resultat['duree_threads']:.3f} s")
    print(f"Gain de performance       : x{resultat['gain']:.1f} plus rapide")
