# cli_modules/traffic_menu.py
#!/usr/bin/env python3
"""
Module de menu pour l'analyse de trafic Illumio.
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from illumio import IllumioTrafficAnalyzer
from cli_modules.menu_utils import print_header, print_menu, get_user_choice, test_connection, initialize_database

def traffic_analysis_menu():
    """Menu pour l'analyse de trafic."""
    print_header()
    print("ANALYSE DE TRAFIC\n")
    
    if not test_connection():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    if not initialize_database():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    print("\nOptions d'analyse de trafic:")
    options = [
        "Créer une nouvelle analyse de trafic",
        "Analyse par entrée manuelle (source/destination/service)",
        "Analyse par importation de fichier Excel",
        "Voir les analyses précédentes",
        "Exporter les résultats d'une analyse"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    if choice == 1:
        create_traffic_analysis()
    elif choice == 2:
        manual_entry_analysis()
    elif choice == 3:
        excel_import_analysis()
    elif choice == 4:
        view_traffic_analyses()
    elif choice == 5:
        export_traffic_analysis()
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

def create_traffic_analysis():
    """Crée une nouvelle analyse de trafic."""
    # Initialiser l'analyseur de trafic
    analyzer = IllumioTrafficAnalyzer()
    
    # Demander les paramètres de l'analyse
    print("\nCréation d'une nouvelle analyse de trafic:")
    query_name = input("Nom de la requête (laisser vide pour un nom automatique): ")
    days = input("Nombre de jours à analyser (défaut: 7): ")
    max_results = input("Nombre maximum de résultats (défaut: 10000): ")
    
    # Utiliser les valeurs par défaut si non spécifiées
    if not query_name:
        query_name = None
    if not days:
        days = 7
    else:
        try:
            days = int(days)
        except ValueError:
            print("Valeur invalide, utilisation de la valeur par défaut (7).")
            days = 7
    
    if not max_results:
        max_results = 10000
    else:
        try:
            max_results = int(max_results)
        except ValueError:
            print("Valeur invalide, utilisation de la valeur par défaut (10000).")
            max_results = 10000
    
    print("\nDémarrage de l'analyse de trafic...")
    start_time = time.time()
    
    # Créer les dates pour l'analyse
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    date_range = (start_date, end_date)
    
    # Exécuter l'analyse de trafic
    results = analyzer.analyze(
        query_name=query_name,
        date_range=date_range,
        max_results=max_results
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    if results:
        print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
        print(f"   {len(results)} flux de trafic récupérés.")
    else:
        print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")

def manual_entry_analysis():
    """Analyse de trafic par entrée manuelle de source, destination et service."""
    print("\nAnalyse de trafic par entrée manuelle:")
    
    # Obtenir les informations source, destination et service
    source_ip = input("Adresse IP source: ")
    dest_ip = input("Adresse IP destination: ")
    
    # Menu pour le protocole
    print("\nChoisissez le protocole:")
    protocols = [
        "TCP (6)",
        "UDP (17)",
        "ICMP (1)",
        "Autre (spécifier)"
    ]
    
    for i, proto in enumerate(protocols, 1):
        print(f"{i}. {proto}")
    
    proto_choice = get_user_choice(len(protocols))
    
    if proto_choice == 0:
        return
    
    # Convertir le choix en numéro de protocole
    if proto_choice == 1:
        protocol = 6  # TCP
    elif proto_choice == 2:
        protocol = 17  # UDP
    elif proto_choice == 3:
        protocol = 1  # ICMP
    else:
        try:
            protocol = int(input("Numéro de protocole: "))
        except ValueError:
            print("Numéro de protocole invalide, utilisation de TCP (6).")
            protocol = 6
    
    # Pour TCP/UDP, demander le port
    port = None
    if protocol in [6, 17]:
        try:
            port = int(input("Port (1-65535): "))
            if port < 1 or port > 65535:
                raise ValueError("Port hors limites")
        except ValueError:
            print("Port invalide, aucun port spécifié.")
            port = None
    
    # Créer une requête d'analyse avec ces paramètres
    analyze_specific_flow(source_ip, dest_ip, protocol, port)

def excel_import_analysis():
    """Analyse de trafic par importation d'un fichier Excel."""
    print("\nAnalyse de trafic par importation de fichier Excel:")
    
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
    
    # Analyser le fichier et créer une requête d'analyse
    analyze_excel_flows(file_path)

def view_traffic_analyses():
    """Affiche la liste des analyses de trafic existantes."""
    print("\nRécupération des analyses de trafic...")
    
    try:
        # Initialiser l'analyseur de trafic
        analyzer = IllumioTrafficAnalyzer()
        
        # Récupérer les requêtes
        queries = analyzer.get_queries()
        
        if not queries:
            print("Aucune analyse de trafic trouvée.")
            return
        
        print(f"\n{len(queries)} analyses trouvées:\n")
        print("-" * 60)
        print(f"{'ID':<8} {'NOM':<30} {'STATUT':<15} {'DATE':<20}")
        print("-" * 60)
        
        for query in queries:
            query_id = query.get('id')
            name = query.get('query_name')
            status = query.get('status')
            created_at = query.get('created_at')
            
            # Limiter la longueur du nom pour l'affichage
            if name and len(name) > 28:
                name = name[:25] + "..."
            
            print(f"{query_id:<8} {name:<30} {status:<15} {created_at:<20}")
        
        print("-" * 60)
        
        # Demander si l'utilisateur veut voir les détails d'une analyse
        query_id = input("\nEntrez l'ID d'une analyse pour voir ses détails (ou appuyez sur Entrée pour revenir): ")
        
        if query_id:
            view_traffic_analysis_details(query_id)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des analyses: {e}")

def view_traffic_analysis_details(query_id):
    """Affiche les détails d'une analyse de trafic spécifique."""
    try:
        # Initialiser l'analyseur de trafic
        analyzer = IllumioTrafficAnalyzer()
        
        # Récupérer les flux
        flows = analyzer.get_flows(query_id)
        
        if not flows:
            print(f"Aucun flux trouvé pour l'analyse {query_id}.")
            return
        
        print(f"\nDétails de l'analyse {query_id}:")
        print(f"{len(flows)} flux de trafic trouvés.")
        
        # Afficher un résumé des flux par décision de politique
        decisions = {}
        for flow in flows:
            decision = flow.get('policy_decision')
            if decision in decisions:
                decisions[decision] += 1
            else:
                decisions[decision] = 1
        
        print("\nRépartition par décision de politique:")
        for decision, count in decisions.items():
            print(f"  - {decision}: {count} flux")
        
        # Demander si l'utilisateur veut voir plus de détails
        show_details = input("\nAfficher les détails des flux? (o/n): ").lower()
        
        if show_details in ('o', 'oui', 'y', 'yes'):
            display_traffic_flows(flows)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des détails: {e}")

def display_traffic_flows(flows, limit=20):
    """Affiche les détails des flux de trafic."""
    print(f"\nAffichage des {min(limit, len(flows))} premiers flux:")
    print("-" * 80)
    print(f"{'SOURCE':<15} {'DESTINATION':<15} {'SERVICE':<20} {'PORT':<8} {'DÉCISION':<15}")
    print("-" * 80)
    
    for i, flow in enumerate(flows):
        if i >= limit:
            print(f"\n... et {len(flows) - limit} autres flux.")
            break
        
        # Extraire les informations correctement selon la structure
        src = flow.get('src', {})
        dst = flow.get('dst', {})
        service = flow.get('service', {})
        
        src_ip = src.get('ip') or 'N/A'
        dst_ip = dst.get('ip') or 'N/A'
        service_name = service.get('name') or 'N/A'
        port = service.get('port') or 'N/A'
        decision = flow.get('policy_decision') or 'N/A'
        
        print(f"{src_ip:<15} {dst_ip:<15} {service_name:<20} {port:<8} {decision:<15}")

def export_traffic_analysis():
    """Exporte les résultats d'une analyse de trafic."""
    print("\nRécupération des analyses de trafic...")
    
    try:
        # Initialiser l'analyseur de trafic
        analyzer = IllumioTrafficAnalyzer()
        
        # Récupérer les requêtes
        queries = analyzer.get_queries()
        
        if not queries:
            print("Aucune analyse de trafic trouvée.")
            return
        
        print(f"\n{len(queries)} analyses trouvées:\n")
        print("-" * 60)
        print(f"{'ID':<8} {'NOM':<30} {'STATUT':<15} {'DATE':<20}")
        print("-" * 60)
        
        for query in queries:
            query_id = query.get('id')
            name = query.get('query_name')
            status = query.get('status')
            created_at = query.get('created_at')
            
            # Limiter la longueur du nom pour l'affichage
            if name and len(name) > 28:
                name = name[:25] + "..."
            
            print(f"{query_id:<8} {name:<30} {status:<15} {created_at:<20}")
        
        print("-" * 60)
        
        # Demander l'ID de l'analyse à exporter
        query_id = input("\nEntrez l'ID de l'analyse à exporter (ou appuyez sur Entrée pour revenir): ")
        
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
        
        # Demander le chemin du fichier
        default_filename = f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}"
        filename = input(f"\nNom du fichier (défaut: {default_filename}): ")
        
        if not filename:
            filename = default_filename
        
        # Exporter selon le format choisi
        format_type = 'csv' if format_choice == 1 else 'json'
        success = analyzer.export_flows(query_id, format_type=format_type, output_file=filename)
        
        if not success:
            print("❌ Erreur lors de l'export.")
    
    except Exception as e:
        print(f"Erreur lors de l'export: {e}")

def analyze_specific_flow(source_ip, dest_ip, protocol, port=None):
    """Analyse un flux spécifique entre source et destination."""
    # Initialiser l'analyseur de trafic
    analyzer = IllumioTrafficAnalyzer()
    
    # Créer un nom de requête spécifique
    query_name = f"Flow_{source_ip}_to_{dest_ip}_{protocol}"
    if port:
        query_name += f"_port{port}"
    
    # Créer une requête d'analyse personnalisée
    # CORRECTION: Formater correctement selon le schéma API Illumio
    query_data = {
        "query_name": query_name,
        "start_date": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d'),
        "sources_destinations_query_op": "and",
        "sources": {
            "include": [
                [{"ip_address": source_ip}]  # Tableaux imbriqués comme requis par le schéma
            ],
            "exclude": []
        },
        "destinations": {
            "include": [
                [{"ip_address": dest_ip}]  # Tableaux imbriqués comme requis par le schéma
            ],
            "exclude": []
        },
        "services": {
            "include": [
                {
                    "proto": protocol,
                    "port": port
                } if port else {"proto": protocol}
            ],
            "exclude": []
        },
        "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
        "max_results": 1000
    }
    
    print("\nDémarrage de l'analyse de trafic spécifique...")
    start_time = time.time()
    
    # Exécuter l'analyse
    results = analyzer.analyze(query_data=query_data)
    
    end_time = time.time()
    duration = end_time - start_time
    
    if results:
        print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
        print(f"   {len(results)} flux de trafic correspondants trouvés.")
        
        # Afficher les résultats
        display_traffic_flows(results)
    else:
        print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")

def analyze_excel_flows(file_path):
    """Analyse les flux spécifiés dans un fichier Excel."""
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
        start_time = time.time()
        
        # Initialiser l'analyseur de trafic
        analyzer = IllumioTrafficAnalyzer()
        
        # Exécuter l'analyse
        results = analyzer.analyze(query_data=query_data)
        
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
                display_traffic_flows(filtered_results)
            else:
                print("   Aucun flux ne correspond exactement à votre demande.")
        else:
            print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")
    
    except ImportError:
        print("❌ Erreur: Module pandas non disponible.")
        print("   Installez-le avec: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse du fichier Excel: {e}")