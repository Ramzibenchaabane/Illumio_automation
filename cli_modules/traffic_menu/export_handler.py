# cli_modules/traffic_menu/export_handler.py
#!/usr/bin/env python3
"""
Module pour l'exportation des résultats d'analyse de trafic.
"""
import os
import traceback
from datetime import datetime

from illumio.utils.directory_manager import get_file_path

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
        
        # Récupérer les requêtes avec gestion d'erreur améliorée
        try:
            queries = analyzer.get_queries()
            if not queries:
                print("Aucune analyse de trafic trouvée.")
                return
        except Exception as e:
            print(f"Erreur lors de la récupération des analyses: {e}")
            print("Détails de l'erreur:")
            traceback.print_exc()
            return
        
        print(f"\n{len(queries)} analyses trouvées.")
        
        # Demander l'ID de l'analyse à exporter
        query_id = get_query_choice(
            queries,
            "\nEntrez l'ID de l'analyse à exporter (ou appuyez sur Entrée pour revenir): "
        )
        
        if not query_id:
            return
        
        # Vérifier que l'analyse existe avec gestion d'erreur améliorée
        try:
            flows = analyzer.get_flows(query_id)
            if not flows:
                print(f"Aucun flux trouvé pour l'analyse {query_id}.")
                return
        except Exception as e:
            print(f"Erreur lors de la récupération des flux pour l'analyse {query_id}: {e}")
            print("Détails de l'erreur:")
            traceback.print_exc()
            return
        
        # Demander le format d'export
        print("\nFormats d'export disponibles:")
        print("1. JSON")
        print("2. Excel (avec feuille de détails des règles)")
        
        format_choice = get_user_choice(2)
        
        if format_choice == 0:
            return
        
        # Demander le nom du fichier
        default_filename = f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}"
        filename = input(f"\nNom du fichier (défaut: {default_filename}): ")
        
        if not filename:
            filename = default_filename
        
        # Déterminer le format d'export
        format_type = None
        if format_choice == 1:
            format_type = 'json'
            if not filename.endswith('.json'):
                filename += '.json'
        else:  # format_choice == 2
            format_type = 'excel'
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
        
        # Construire le chemin complet du fichier de sortie
        output_path = get_file_path(filename, 'output')
        
        try:
            # Utiliser la méthode export_query_results qui a été mise à jour pour inclure les règles
            success = analyzer.export_handler.export_query_results(query_id, format_type=format_type, output_file=output_path)
            
            if success:
                print(f"\n✅ Exportation réussie vers {output_path}")
            else:
                print("\n❌ Erreur lors de l'export.")
        except Exception as e:
            print(f"\n❌ Erreur lors de l'export: {e}")
            print("Détails de l'erreur:")
            traceback.print_exc()
    
    except Exception as e:
        print(f"Erreur lors de l'export: {e}")
        print("Détails de l'erreur:")
        traceback.print_exc()