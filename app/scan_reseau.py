import socket
import subprocess
import platform
import ipaddress
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from exceptions_reseau import ReseauInvalideError

# Logger du module, rattaché à la configuration définie dans main.py (operations.log)
logger = logging.getLogger(__name__)

# Système d'exploitation courant (détecté une seule fois au chargement du module)
_SYSTEME = platform.system().lower()


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


def reverse_dns(ip):
    """Résout une adresse IP en nom de machine (DNS inverse).

    Retourne le nom trouvé, ou None si aucune correspondance."""
    try:
        nom = socket.gethostbyaddr(ip)[0]
        return nom
    except Exception:
        # Pas d'enregistrement PTR pour cette adresse : cas normal, pas une erreur bloquante
        return None


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
        # -n 1 : un seul envoi, -w 1000 : timeout en millisecondes
        return ["ping", "-n", "1", "-w", "1000"] + option_ipv6 + [str(ip)]
    else:
        # -c 1 : un seul envoi, -W 1 : timeout en secondes (Linux/Mac)
        return ["ping", "-c", "1", "-W", "1"] + option_ipv6 + [str(ip)]


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


def scanner_plage_threads(reseau_cidr, max_workers=100):
    """Scanne une plage d'adresses AVEC threads. Retourne (liste_resultats_vivants, duree).
    Lève ReseauInvalideError si la notation CIDR est invalide."""
    debut = time.perf_counter()
    hotes = _lister_hotes(reseau_cidr)

    vivants = []
    # Chaque hôte est pingé dans un thread du pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        resultats = executor.map(scanner_ip, hotes)
        for resultat in resultats:
            if resultat["vivant"]:
                vivants.append(resultat)

    # Tri des résultats par adresse IP pour un affichage stable
    vivants.sort(key=lambda r: ipaddress.ip_address(r["ip"]))
    duree = time.perf_counter() - debut
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
        vivants, duree = scanner_plage_threads(cidr)
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
