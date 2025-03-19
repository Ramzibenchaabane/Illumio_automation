# cli_modules/traffic_menu/export_handler.py
#!/usr/bin/env python3
"""
Module pour l'exportation des résultats d'analyse de trafic.
"""
import os
from datetime import datetime

from illumio.utils.directory_manager import get_output_dir, get_file_path

from cli_modules.menu_utils import get_user_choice
from .common import (
    initialize_analyzer,
    print_analysis_header,
    get_query_choice
)

def export_traffic_analysis():
    """Exporte les résultats d'une analyse de trafic."""
    print_analysis_header("EXPORTATION DES RÉSULTATS D'ANALYSE")
    
    try:
        # Initialiser l'analyseur de trafic
        analyzer = initialize_analyzer()
        if not analyzer:
            return
        
        # Récupérer les requêtes
        queries = analyzer.get_queries()
        
        if not queries:
            print("Aucune analyse de trafic trouvée.")
            return
        
        print(f"\n{len(queries)} analyses trouvées.")
        
        # Demander l'ID de l'analyse à exporter
        query_id = get_query_choice(
            queries,
            "\nEntrez l'ID de l'analyse à exporter (ou appuyez sur Entrée pour revenir): "
        )
        
        if not query_id:
            return
        
        # Vérifier que l'analyse existe
        flows = analyzer.get_flows(query_id)
        if not flows:
            print(f"Aucun flux trouvé pour l'analyse {query_id}.")
            return
        
        # Demander le format d'export
        print("\nFormats d'export disponibles:")
        print("1. CSV")
        print("2. JSON")
        
        format_choice = get_user_choice(2)
        
        if format_choice == 0:
            return
        
        # Récupérer le répertoire de sortie
        output_dir = get_output_dir()
        
        # Demander le nom du fichier
        default_filename = f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}"
        filename = input(f"\nNom du fichier (défaut: {default_filename}): ")
        
        if not filename:
            filename = default_filename
        
        # Exporter selon le format choisi
        format_type = 'csv' if format_choice == 1 else 'json'
        
        # S'assurer que le nom du fichier a l'extension correcte
        if not filename.endswith(f'.{format_type}'):
            filename += f'.{format_type}'
        
        # Construire le chemin complet du fichier de sortie
        output_path = get_file_path(filename, 'output')
        
        success = analyzer.export_flows(query_id, format_type=format_type, output_file=output_path)
        
        if success:
            print(f"\n✅ Exportation réussie vers {output_path}")
        else:
            print("\n❌ Erreur lors de l'export.")
    
    except Exception as e:
        print(f"Erreur lors de l'export: {e}")