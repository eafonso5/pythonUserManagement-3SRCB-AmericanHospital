import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

VILLES = ["paris", "marseille", "rennes", "grenoble"]

# Création automatique des dossiers au démarrage
for ville in VILLES:
    chemin = os.path.join("ftp_server", ville)
    os.makedirs(chemin, exist_ok=True)
    print(f"Dossier prêt : {chemin}")

# Configuration des utilisateurs du serveur de test
authorizer = DummyAuthorizer()
authorizer.add_user("admin", "password", "./ftp_server", perm="elradfmwMT")

handler = FTPHandler
handler.authorizer = authorizer

# Lance le serveur sur l'adresse locale (127.0.0.1) port 2121
server = FTPServer(("127.0.0.1", 2121), handler)
print("Serveur FTP de test lancé sur le port 2121...")
server.serve_forever()