# cli_modules/traffic_menu/menu.py
#!/usr/bin/env python3
"""
Module principal du menu d'analyse de trafic.
"""
from cli_modules.menu_utils import print_header, print_menu, get_user_choice
from .common import validate_connection
from .analysis_creator import create_traffic_analysis, launch_deep_rule_analysis
from .analysis_viewer import view_traffic_analyses
from .flow_analyzer import manual_entry_analysis
from .excel_processor import excel_import_analysis
from .export_handler import export_traffic_analysis

def traffic_analysis_menu():
    """Menu principal pour l'analyse de trafic."""
    # Afficher l'en-tête
    print_header()
    print("ANALYSE DE TRAFIC\n")
    
    # Vérifier la connexion et l'initialisation de la base de données
    if not validate_connection():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    # Afficher le menu des options
    print("\nOptions d'analyse de trafic:")
    options = [
        "Créer une nouvelle analyse de trafic",
        "Analyse par entrée manuelle (source/destination/service)",
        "Analyse par importation de fichier Excel",
        "Voir les analyses précédentes",
        "Exporter les résultats d'une analyse",
        "Lancer une analyse approfondie des règles sur une analyse existante"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    # Traiter le choix de l'utilisateur
    if choice == 0:
        return
    
    # Rediriger vers la fonction appropriée
    handlers = {
        1: create_traffic_analysis,
        2: manual_entry_analysis,
        3: excel_import_analysis,
        4: view_traffic_analyses,
        5: export_traffic_analysis,
        6: launch_deep_rule_analysis
    }
    
    # Appeler la fonction correspondante
    if choice in handlers:
        handlers[choice]()
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")