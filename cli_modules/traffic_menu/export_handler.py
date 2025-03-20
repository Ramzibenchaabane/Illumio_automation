# cli_modules/traffic_menu/export_handler.py
#!/usr/bin/env python3
"""
Module pour l'exportation des résultats d'analyse de trafic.
"""
import os
import traceback
import json
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
        
        try:
            success = analyzer.export_flows(query_id, format_type=format_type, output_file=output_path)
            
            if success:
                print(f"\n✅ Exportation réussie vers {output_path}")
            else:
                print("\n❌ Erreur lors de l'export.")
                
                # Alternative manuelle d'export si la méthode principale échoue
                print("\nTentative d'export alternatif...")
                if export_flows_manually(flows, output_path, format_type):
                    print(f"\n✅ Export alternatif réussi vers {output_path}")
                else:
                    print("\n❌ L'export alternatif a également échoué.")
        except Exception as e:
            print(f"\n❌ Erreur lors de l'export: {e}")
            print("Détails de l'erreur:")
            traceback.print_exc()
            
            # Tentative d'export manuel
            print("\nTentative d'export alternatif...")
            if export_flows_manually(flows, output_path, format_type):
                print(f"\n✅ Export alternatif réussi vers {output_path}")
            else:
                print("\n❌ L'export alternatif a également échoué.")
    
    except Exception as e:
        print(f"Erreur lors de l'export: {e}")
        print("Détails de l'erreur:")
        traceback.print_exc()

def export_flows_manually(flows, output_file, format_type):
    """
    Méthode alternative pour exporter les flux manuellement si la méthode principale échoue.
    
    Args:
        flows (list): Liste des flux à exporter
        output_file (str): Chemin du fichier de sortie
        format_type (str): Format d'export ('csv' ou 'json')
        
    Returns:
        bool: True si l'export a réussi, False sinon
    """
    try:
        if format_type.lower() == 'json':
            # Convertir tous les objets non JSON-sérialisables en dictionnaires
            def prepare_for_json(obj):
                if isinstance(obj, dict):
                    return {k: prepare_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [prepare_for_json(i) for i in obj]
                elif hasattr(obj, '__dict__'):
                    return prepare_for_json(obj.__dict__)
                else:
                    try:
                        # Tenter de convertir en type de base
                        return json.loads(json.dumps(obj))
                    except:
                        # Sinon, convertir en chaîne
                        return str(obj)
            
            # Préparer les données pour JSON
            prepared_flows = [prepare_for_json(flow) for flow in flows]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(prepared_flows, f, indent=2, ensure_ascii=False)
            
            return True
            
        elif format_type.lower() == 'csv':
            import csv
            
            # Définir les en-têtes CSV en fonction des données disponibles
            fieldnames = [
                'src_ip', 'dst_ip', 'service_name', 'service_port', 'service_protocol',
                'policy_decision', 'flow_direction', 'num_connections',
                'rule_href', 'rule_name'
            ]
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for flow in flows:
                    if not isinstance(flow, dict):
                        if hasattr(flow, '__dict__'):
                            flow = flow.__dict__
                        else:
                            continue
                    
                    # Extraire les données importantes
                    src_ip = None
                    dst_ip = None
                    service_name = None
                    service_port = None
                    service_protocol = None
                    
                    # Tenter d'extraire les données imbriquées
                    if 'src' in flow and isinstance(flow['src'], dict):
                        src_ip = flow['src'].get('ip')
                    elif 'src_ip' in flow:
                        src_ip = flow.get('src_ip')
                    
                    if 'dst' in flow and isinstance(flow['dst'], dict):
                        dst_ip = flow['dst'].get('ip')
                    elif 'dst_ip' in flow:
                        dst_ip = flow.get('dst_ip')
                    
                    if 'service' in flow:
                        if isinstance(flow['service'], dict):
                            service_name = flow['service'].get('name')
                            service_port = flow['service'].get('port')
                            service_protocol = flow['service'].get('proto')
                        else:
                            service_name = flow.get('service')
                    
                    if 'service_name' in flow:
                        service_name = flow.get('service_name')
                    if 'service_port' in flow:
                        service_port = flow.get('service_port')
                    if 'service_protocol' in flow:
                        service_protocol = flow.get('service_protocol')
                    
                    # Extraire les informations de règles si disponibles
                    rule_href = None
                    rule_name = None
                    
                    if 'rule_href' in flow:
                        rule_href = flow.get('rule_href')
                        rule_name = flow.get('rule_name')
                    elif 'rules' in flow:
                        rules = flow['rules']
                        if isinstance(rules, dict) and 'sec_policy' in rules:
                            sec_policy = rules.get('sec_policy', {})
                            if isinstance(sec_policy, dict):
                                rule_href = sec_policy.get('href')
                                rule_name = sec_policy.get('name')
                        elif isinstance(rules, list) and len(rules) > 0:
                            rule = rules[0]
                            if isinstance(rule, dict):
                                rule_href = rule.get('href')
                                rule_name = rule.get('name', rule_href.split('/')[-1] if rule_href else None)
                    
                    # Préparer la ligne CSV
                    csv_row = {
                        'src_ip': src_ip,
                        'dst_ip': dst_ip,
                        'service_name': service_name,
                        'service_port': service_port,
                        'service_protocol': service_protocol,
                        'policy_decision': flow.get('policy_decision'),
                        'flow_direction': flow.get('flow_direction'),
                        'num_connections': flow.get('num_connections'),
                        'rule_href': rule_href,
                        'rule_name': rule_name
                    }
                    
                    writer.writerow(csv_row)
            
            return True
        
        else:
            print(f"Format non supporté: {format_type}")
            return False
            
    except Exception as e:
        print(f"Erreur lors de l'export manuel: {e}")
        traceback.print_exc()
        return False