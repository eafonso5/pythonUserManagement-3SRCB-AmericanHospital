from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# Configuration des utilisateurs du serveur de test
authorizer = DummyAuthorizer()
# On crée un utilisateur 'admin' avec le mdp 'password' qui a tous les droits (elradfmwMT)
authorizer.add_user("admin", "password", "./data_hospital", perm="elradfmwMT")

handler = FTPHandler
handler.authorizer = authorizer

# Lance le serveur sur l'adresse locale (127.0.0.1) port 2121
server = FTPServer(("127.0.0.1", 2121), handler)
print("Serveur FTP de test lancé sur le port 2121...")
server.serve_forever()