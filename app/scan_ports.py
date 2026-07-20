import socket
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from exceptions_reseau import PlagePortsInvalideError

# Logger du module, rattaché à la configuration définie dans main.py (operations.log)
logger = logging.getLogger(__name__)

# Cible par défaut : la machine locale (scan autorisé sans risque légal)
HOTE_DEFAUT = "127.0.0.1"

# Ports des protocoles bien connus (IANA well-known + services répandus),
# utilisés pour enrichir l'affichage des résultats de scan.
SERVICES_CONNUS = {
    # Services système et historiques (0-99)
    1: "TCPMUX", 7: "Echo", 9: "Discard", 13: "Daytime", 17: "QOTD",
    19: "CHARGEN", 20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 37: "Time", 43: "WHOIS", 49: "TACACS", 53: "DNS",
    67: "DHCP (serveur)", 68: "DHCP (client)", 69: "TFTP", 70: "Gopher",
    79: "Finger", 80: "HTTP", 88: "Kerberos",
    # Messagerie, annuaire, gestion (100-599)
    102: "ISO-TSAP", 110: "POP3", 111: "RPCbind", 113: "Ident", 119: "NNTP",
    123: "NTP", 135: "MS-RPC", 137: "NetBIOS-NS", 138: "NetBIOS-DGM",
    139: "NetBIOS-SSN", 143: "IMAP", 161: "SNMP", 162: "SNMP-Trap",
    179: "BGP", 194: "IRC", 264: "BGMP", 389: "LDAP", 443: "HTTPS",
    445: "SMB", 465: "SMTPS", 500: "ISAKMP/IKE", 514: "Syslog", 515: "LPD/LPR",
    520: "RIP", 521: "RIPng", 540: "UUCP", 546: "DHCPv6 (client)",
    547: "DHCPv6 (serveur)", 554: "RTSP", 587: "SMTP (submission)",
    593: "MS-RPC/HTTP",
    # Sécurité, bases de données, VPN, services applicatifs (600-9999)
    623: "IPMI", 636: "LDAPS", 989: "FTPS-data", 990: "FTPS", 993: "IMAPS",
    995: "POP3S", 1080: "SOCKS", 1194: "OpenVPN", 1433: "MS-SQL",
    1434: "MS-SQL-Monitor", 1521: "Oracle", 1701: "L2TP", 1723: "PPTP",
    1812: "RADIUS (auth)", 1813: "RADIUS (compta)", 1883: "MQTT",
    2049: "NFS", 2082: "cPanel", 2083: "cPanel (SSL)", 2181: "ZooKeeper",
    2375: "Docker", 2376: "Docker (TLS)", 3128: "Squid-Proxy",
    3268: "LDAP-GC", 3269: "LDAP-GC (SSL)", 3306: "MySQL", 3389: "RDP",
    3690: "SVN", 4369: "Erlang-EPMD", 5000: "UPnP/Flask", 5060: "SIP",
    5061: "SIP-TLS", 5222: "XMPP (client)", 5269: "XMPP (serveur)",
    5353: "mDNS", 5432: "PostgreSQL", 5601: "Kibana", 5672: "AMQP",
    5683: "CoAP", 5900: "VNC", 5984: "CouchDB", 6379: "Redis",
    6443: "Kubernetes-API", 6667: "IRC", 7001: "WebLogic", 8000: "HTTP-alt",
    8080: "HTTP-Proxy", 8443: "HTTPS-alt", 8883: "MQTT (TLS)", 9000: "SonarQube",
    9042: "Cassandra", 9092: "Kafka", 9200: "Elasticsearch",
    9300: "Elasticsearch (noeud)",
    # Ports hauts courants (>=10000)
    11211: "Memcached", 15672: "RabbitMQ-Mgmt", 27017: "MongoDB",
    27018: "MongoDB (shard)", 50000: "SAP/DB2",
    # Compléments : autres protocoles et services répandus
    2: "CompressNet", 11: "SYSTAT", 15: "NETSTAT", 42: "WINS", 101: "Hostname",
    104: "DICOM", 109: "POP2", 115: "SFTP (simple)", 177: "XDMCP", 199: "SMUX",
    311: "AppleShare-Admin", 383: "HP-Alarm-Mgr", 427: "SLP", 434: "Mobile-IP",
    444: "SNPP", 464: "Kerberos-kpasswd", 497: "Retrospect", 512: "rexec",
    513: "rlogin", 517: "talk", 518: "ntalk", 523: "IBM-DB2", 524: "NetWare-NCP",
    543: "klogin", 544: "kshell", 548: "AFP", 563: "NNTPS", 631: "IPP",
    639: "MSDP", 646: "LDP", 749: "Kerberos-adm", 783: "SpamAssassin",
    830: "NETCONF/SSH", 843: "Flash-Policy", 853: "DNS-over-TLS", 860: "iSCSI",
    873: "rsync", 902: "VMware-ESXi", 992: "Telnet-TLS", 1025: "NFS/IIS",
    1099: "Java-RMI", 1241: "Nessus", 1311: "Dell-OpenManage", 1352: "Lotus-Notes",
    1414: "IBM-MQ", 1494: "Citrix-ICA", 1719: "H.323-RAS", 1720: "H.323",
    1755: "MS-Media", 1801: "MSMQ", 1863: "MSN", 1900: "SSDP", 1935: "RTMP",
    2000: "Cisco-SCCP", 2222: "EtherNet/IP", 2379: "etcd (client)",
    2380: "etcd (pair)", 2404: "IEC-104 (SCADA)", 2427: "MGCP", 2483: "Oracle-DB",
    2484: "Oracle-DB (SSL)", 2525: "SMTP-alt", 2575: "HL7", 2598: "Citrix-CGP",
    2601: "Zebra", 2604: "OSPF-Quagga", 2638: "Sybase", 2947: "GPSD",
    3000: "Grafana/Node-dev", 3050: "Firebird", 3260: "iSCSI-Target",
    3283: "Apple-Remote-Desktop", 3299: "SAP-Router", 3478: "STUN/TURN",
    3493: "NUT-UPS", 3544: "Teredo", 3632: "distcc", 3689: "DAAP",
    3702: "WS-Discovery", 3868: "Diameter", 4040: "Spark-UI", 4500: "IPsec-NAT-T",
    4662: "eMule", 4789: "VXLAN", 4840: "OPC-UA", 4843: "OPC-UA (TLS)",
    4899: "Radmin", 5001: "iperf", 5004: "RTP", 5005: "RTP-ctrl",
    5044: "Logstash-Beats", 5190: "AIM/ICQ", 5280: "XMPP-BOSH",
    5349: "STUN/TURN (TLS)", 5351: "NAT-PMP", 5355: "LLMNR", 5357: "WSDAPI",
    5555: "ADB", 5631: "pcAnywhere (data)", 5632: "pcAnywhere", 5666: "Nagios-NRPE",
    5671: "AMQPS", 5684: "CoAP (DTLS)", 5701: "Hazelcast", 5800: "VNC-HTTP",
    5938: "TeamViewer", 5985: "WinRM-HTTP", 5986: "WinRM-HTTPS", 6000: "X11",
    6514: "Syslog-TLS", 6566: "SANE", 6600: "MPD", 6697: "IRC (TLS)",
    6881: "BitTorrent", 6969: "BitTorrent-Tracker", 7000: "Cassandra (noeud)",
    7070: "RealServer", 7199: "Cassandra-JMX", 7474: "Neo4j (HTTP)",
    7547: "TR-069-CWMP", 7680: "Windows-Update", 7687: "Neo4j-Bolt",
    8005: "Tomcat (arret)", 8009: "AJP", 8020: "Hadoop-NameNode",
    8086: "InfluxDB", 8088: "Hadoop-YARN", 8091: "Couchbase", 8140: "Puppet",
    8291: "MikroTik-Winbox", 8333: "Bitcoin", 8384: "Syncthing", 8500: "Consul",
    8530: "WSUS", 8531: "WSUS (SSL)", 8728: "MikroTik-API", 8888: "Jupyter",
    9001: "Tor", 9090: "Prometheus", 9091: "Transmission", 9093: "Alertmanager",
    9100: "Imprimante (RAW)", 9160: "Cassandra-Thrift", 9418: "Git",
    9987: "TeamSpeak3", 10000: "Webmin/NDMP", 10050: "Zabbix-Agent",
    10051: "Zabbix-Server", 10250: "Kubelet", 11112: "DICOM (alt)",
    16509: "libvirt", 17500: "Dropbox-LAN", 19132: "Minecraft-Bedrock",
    20000: "DNP3/Usermin", 25565: "Minecraft", 27015: "Source-Games",
    28015: "RethinkDB", 32400: "Plex", 33060: "MySQL-X", 44818: "EtherNet/IP",
    47808: "BACnet",
    # Ports propres au projet
    2121: "FTP (serveur de test)", 5050: "Chat interne",
}


def nom_service(port):
    """Retourne le nom du service associé à un port, ou 'inconnu'."""
    return SERVICES_CONNUS.get(port, "inconnu")


def _log_dimension_pool(proto, n_taches, max_workers, workers, verbose):
    """(verbose) Affiche le dimensionnement du pool de threads avant un scan."""
    if not verbose:
        return
    print(f"[verbose] {n_taches} tâche(s) {proto}, max_workers demandé={max_workers} "
          f"-> {workers} thread(s) effectif(s)")
    if workers > 2000:
        print(f"[verbose] ATTENTION : {workers} threads simultanés demandés, "
              f"risque de saturation (échec possible de création de threads).")


def _log_echec_pool(prefixe, workers, exc, verbose):
    """(verbose + journal) Signale un échec de création/exécution du pool de threads."""
    msg = f"échec du pool de threads ({workers} workers) : {type(exc).__name__}: {exc}"
    if verbose:
        print(f"[verbose] ÉCHEC -> {msg}")
    logger.error(f"{prefixe} : {msg}")


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


def scanner_plage_threads(hote, port_debut, port_fin, timeout=0.5, max_workers=32768, verbose=False):
    """Scanne une plage de ports AVEC threads (ThreadPoolExecutor, bibliothèque standard).

    Retourne un tuple (liste_ports_ouverts, duree_en_secondes).
    Lève PlagePortsInvalideError si la plage est invalide.

    verbose=True affiche le dimensionnement du pool, une progression régulière et
    signale explicitement un échec de création de threads (max_workers trop élevé)."""
    _valider_plage(port_debut, port_fin)
    debut = time.perf_counter()
    ports = list(range(port_debut, port_fin + 1))

    # Inutile d'allouer plus de threads que de ports à tester
    workers = min(max_workers, len(ports)) or 1
    _log_dimension_pool("TCP", len(ports), max_workers, workers, verbose)

    ports_ouverts = []
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            if verbose:
                print(f"[verbose] pool créé ({workers} workers), scan en cours...")
            resultats = {port: executor.submit(scanner_un_port, hote, port, timeout)
                         for port in ports}

            traites = 0
            for port, futur in resultats.items():
                traites += 1
                if futur.result():
                    ports_ouverts.append(port)
                if verbose and traites % 5000 == 0:
                    print(f"[verbose] {traites}/{len(ports)} ports testés, "
                          f"{len(ports_ouverts)} ouvert(s)")
    except (RuntimeError, MemoryError, OSError) as e:
        _log_echec_pool("SCAN PORTS", workers, e, verbose)
        raise

    ports_ouverts.sort()
    duree = time.perf_counter() - debut
    if verbose:
        print(f"[verbose] terminé en {duree:.3f}s, {len(ports_ouverts)} ouvert(s)")
    logger.info(
        f"SCAN PORTS THREADS : {hote} [{port_debut}-{port_fin}] -> "
        f"{len(ports_ouverts)} ouvert(s) {ports_ouverts} en {duree:.3f}s"
    )
    return ports_ouverts, duree


def scanner_tous_les_ports(hote, timeout=0.5, max_workers=32768, verbose=False):
    """Scanne la totalité des ports (1 à 65535) en parallèle via les threads."""
    logger.info(f"SCAN COMPLET DÉMARRÉ : {hote} (1-65535)")
    return scanner_plage_threads(hote, 1, 65535, timeout, max_workers, verbose)


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


def scanner_plage_udp_threads(hote, port_debut, port_fin, timeout=1.0, max_workers=32768, verbose=False):
    """Scanne une plage de ports UDP AVEC threads.

    Retourne (liste de tuples (port, statut) hors 'fermé'/'erreur', duree).
    Lève PlagePortsInvalideError si la plage est invalide.
    verbose=True : dimensionnement du pool, progression et échec de threads détaillés."""
    _valider_plage(port_debut, port_fin)
    debut = time.perf_counter()
    ports = list(range(port_debut, port_fin + 1))

    workers = min(max_workers, len(ports)) or 1
    _log_dimension_pool("UDP", len(ports), max_workers, workers, verbose)

    resultats = []
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            if verbose:
                print(f"[verbose] pool créé ({workers} workers), scan UDP en cours...")
            futurs = {port: executor.submit(scanner_un_port_udp, hote, port, timeout)
                      for port in ports}
            traites = 0
            for port, futur in futurs.items():
                traites += 1
                statut = futur.result()
                # On ignore les ports clairement fermés et les erreurs techniques
                if statut not in ("fermé", "erreur"):
                    resultats.append((port, statut))
                if verbose and traites % 5000 == 0:
                    print(f"[verbose] {traites}/{len(ports)} ports testés, "
                          f"{len(resultats)} non fermé(s)")
    except (RuntimeError, MemoryError, OSError) as e:
        _log_echec_pool("SCAN UDP", workers, e, verbose)
        raise

    resultats.sort()
    duree = time.perf_counter() - debut
    if verbose:
        print(f"[verbose] terminé en {duree:.3f}s, {len(resultats)} non fermé(s)")
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
            ports_ouverts, duree = scanner_plage_threads(hote, port_debut, port_fin, verbose=True)
            _afficher_ports_ouverts(ports_ouverts)
            print(f"Temps [TCP] : {duree:.3f} seconde(s).")

        if "udp" in protocoles:
            print(f"\n[UDP] Scan de {hote} [{port_debut}-{port_fin}] en cours...")
            print("(UDP : seuls les ports clairement fermés sont écartés)")
            resultats, duree = scanner_plage_udp_threads(hote, port_debut, port_fin, verbose=True)
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
            ports_ouverts, duree = scanner_tous_les_ports(hote, verbose=True)
            _afficher_ports_ouverts(ports_ouverts)
            print(f"Temps [TCP] : {duree:.3f} seconde(s).")

        if "udp" in protocoles:
            print(f"\n[UDP] Scan complet de {hote} en cours...")
            resultats, duree = scanner_plage_udp_threads(hote, 1, 65535, verbose=True)
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
