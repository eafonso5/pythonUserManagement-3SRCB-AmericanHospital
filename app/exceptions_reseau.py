"""Exceptions personnalisées pour les modules réseau du T3.

Elles sont levées explicitement par les fonctions « cœur » (scan de ports, scan
réseau, serveur de chat) et attrapées par la couche interactive (menu) afin
d'afficher un message clair à l'utilisateur. Répond à la consigne du sujet :
« générer les exceptions »."""


class ErreurReseau(Exception):
    """Classe de base pour toutes les erreurs des modules réseau du T3."""


class PlagePortsInvalideError(ErreurReseau):
    """Levée quand une plage de ports est invalide (hors 1-65535 ou début > fin)."""


class ReseauInvalideError(ErreurReseau):
    """Levée quand une notation réseau/CIDR est invalide (ex : 'pas_un_reseau')."""


class PseudoInvalideError(ErreurReseau):
    """Levée quand un client de chat fournit un pseudo vide."""
