"""
Module de gestion de la base de données SQLite pour l'application Illumio.
Ce fichier est maintenu pour la compatibilité et redirige vers la nouvelle
structure modulaire dans le package database.
"""
from .database.core import IllumioDatabase

# Exporter la classe principale pour maintenir la compatibilité
__all__ = ['IllumioDatabase']