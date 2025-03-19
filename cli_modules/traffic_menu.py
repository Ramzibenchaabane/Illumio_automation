# cli_modules/traffic_menu.py
#!/usr/bin/env python3
"""
Module de menu pour l'analyse de trafic Illumio.
Ce fichier est maintenu pour des raisons de compatibilité et
redirige vers l'implémentation modulaire dans le sous-package traffic_menu.
"""
from cli_modules.traffic_menu import traffic_analysis_menu

# Re-exporter la fonction pour maintenir la compatibilité avec le code existant
__all__ = ['traffic_analysis_menu']