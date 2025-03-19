# cli_modules/traffic_menu/excel_processor.py
#!/usr/bin/env python3
"""
Module pour l'analyse de trafic via l'importation de fichiers Excel.
"""
import os
import time
from datetime import datetime, timedelta

import pandas as pd

from .common import (
    initialize_analyzer,
    print_analysis_header,
    FlowDisplayFormatter
)

def excel_import_analysis():
    """Analyse de trafic par importation d'un fichier Excel."""
    print_analysis_header("ANALYSE DE TRAFIC PAR IMPORTATION DE FICHIER EXCEL")
    
    # Demander le chemin du fichier
    file_path = input("Chemin du fichier Excel (.xlsx): ")
    
    if not file_path:
        print("Aucun fichier spécifié.")
        return
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas.")
        return
    
    if not file_path.endswith(('.xlsx', '.xls')):
        print("Le fichier doit être au format Excel (.xlsx ou .xls).")
        return
    
    # Demander si l'analyse de règles approfondie doit être effectuée
    deep_analysis = input("\nEffectuer une analyse de règles approfondie ? (o/N): ").lower()
    perform_deep_analysis = deep_analysis in ('o', 'oui', 'y', 'yes')
    
    # Analyser le fichier et créer une requête d'analyse
    analyze_excel_flows(file_path, perform_deep_analysis)

def analyze_excel_flows(file_path, perform_deep_analysis=False):
    """
    Analyse les flux spécifiés dans un fichier Excel.
    
    Args:
        file_path (str): Chemin vers le fichier Excel
        perform_deep_analysis (bool): Si True, effectuer analyse de règles approfondie
    """
    try:
        print("\nChargement du fichier Excel...")
        
        # Lire le fichier Excel
        df = pd.read_excel(file_path)
        
        # Vérifier que les colonnes requises sont présentes
        required_columns = ['source', 'destination', 'protocol']
        for col in required_columns:
            if col not in df.columns:
                print(f"Erreur: La colonne '{col}' est manquante dans le fichier Excel.")
                print(f"Colonnes trouvées: {', '.join(df.columns)}")
                return
        
        # Convertir les protocoles textuels en numéros
        protocol_map = {
            'TCP': 6,
            'UDP': 17,
            'ICMP': 1
        }
        
        # Initialiser une liste pour stocker les flux à analyser
        flows = []
        
        # Parcourir les lignes du DataFrame
        for _, row in df.iterrows():
            source = str(row['source']).strip()
            destination = str(row['destination']).strip()
            
            # Gérer le protocole (texte ou nombre)
            protocol = row['protocol']
            if isinstance(protocol, str):
                protocol = protocol.upper().strip()
                protocol = protocol_map.get(protocol, None)
                if protocol is None:
                    try:
                        protocol = int(row['protocol'])
                    except ValueError:
                        print(f"Protocole invalide '{row['protocol']}' pour {source}->{destination}, ignoré.")
                        continue
            
            # Gérer le port s'il est présent
            port = None
            if 'port' in df.columns:
                try:
                    if not pd.isna(row['port']):
                        port = int(row['port'])
                        if port < 1 or port > 65535:
                            print(f"Port hors limites {port} pour {source}->{destination}, port ignoré.")
                            port = None
                except (ValueError, TypeError):
                    print(f"Port invalide '{row['port']}' pour {source}->{destination}, port ignoré.")
            
            # Ajouter ce flux à la liste
            flows.append({
                'source': source,
                'destination': destination,
                'protocol': protocol,
                'port': port
            })
        
        if not flows:
            print("Aucun flux valide trouvé dans le fichier Excel.")
            return
        
        print(f"{len(flows)} flux ont été identifiés dans le fichier Excel.")
        
        # Demander confirmation
        confirm = input("Voulez-vous lancer l'analyse de ces flux? (o/n): ").lower()
        if confirm not in ('o', 'oui', 'y', 'yes'):
            print("Analyse annulée.")
            return
        
        # Initialiser l'analyseur de trafic
        analyzer = initialize_analyzer()
        if not analyzer:
            return
        
        # Créer une requête d'analyse globale pour tous les flux
        query_name = f"Excel_Flows_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Structurer la requête pour inclure tous les flux
        # CORRECTION: Formater correctement selon le schéma API Illumio
        sources_include = []
        destinations_include = []
        services_include = []
        
        # Collecter toutes les sources et destinations uniques
        unique_sources = set(flow['source'] for flow in flows)
        unique_destinations = set(flow['destination'] for flow in flows)
        
        # Format correct pour l'API: tableaux imbriqués pour sources/destinations
        for source in unique_sources:
            sources_include.append([{"ip_address": source}])
        
        for destination in unique_destinations:
            destinations_include.append([{"ip_address": destination}])
        
        # Organiser les services uniques (protocole/port)
        for flow in flows:
            service_entry = {"proto": flow['protocol']}
            if flow['port']:
                service_entry["port"] = flow['port']
            
            # Vérifier s'il existe déjà un service identique
            if service_entry not in services_include:
                services_include.append(service_entry)
        
        # Créer la requête finale
        query_data = {
            "query_name": query_name,
            "start_date": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            "end_date": datetime.now().strftime('%Y-%m-%d'),
            "sources_destinations_query_op": "or",  # Utiliser OR pour permettre tous les flux
            "sources": {
                "include": sources_include,
                "exclude": []
            },
            "destinations": {
                "include": destinations_include,
                "exclude": []
            },
            "services": {
                "include": services_include,
                "exclude": []
            },
            "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
            "max_results": 10000
        }
        
        print("\nDémarrage de l'analyse des flux Excel...")
        if perform_deep_analysis:
            print("L'analyse de règles approfondie sera effectuée après l'analyse de trafic.")
            
        start_time = time.time()
        
        # Exécuter l'analyse
        results = analyzer.analyze(query_data=query_data, perform_deep_analysis=perform_deep_analysis)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if results:
            print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
            print(f"   {len(results)} flux de trafic correspondants trouvés.")
            
            # Filtrer les résultats pour ne garder que les flux qui correspondent à la demande
            filtered_results = []
            for result in results:
                src_ip = result.get('src', {}).get('ip')
                dst_ip = result.get('dst', {}).get('ip')
                proto = result.get('service', {}).get('proto')
                result_port = result.get('service', {}).get('port')
                
                # Vérifier si ce résultat correspond à l'un des flux demandés
                for flow in flows:
                    if (src_ip == flow['source'] and 
                        dst_ip == flow['destination'] and 
                        proto == flow['protocol'] and
                        (flow['port'] is None or result_port == flow['port'])):
                        filtered_results.append(result)
                        break
            
            if filtered_results:
                print(f"   {len(filtered_results)} flux correspondent exactement à votre demande.")
                FlowDisplayFormatter.format_flow_table(filtered_results)
            else:
                print("   Aucun flux ne correspond exactement à votre demande.")
        else:
            print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")
    
    except ImportError:
        print("❌ Erreur: Module pandas non disponible.")
        print("   Installez-le avec: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse du fichier Excel: {e}")