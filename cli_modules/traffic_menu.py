#cli_modues/traffic_menu.py
#!/usr/bin/env python3
import time
import json
from datetime import datetime, timedelta
from illumio import IllumioAPI, TrafficAnalysisOperation
from illumio.database import IllumioDatabase
from traffic_analysis import analyze_traffic
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
        view_traffic_analyses()
    elif choice == 3:
        export_traffic_analysis()
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

def create_traffic_analysis():
    """Crée une nouvelle analyse de trafic."""
    # Demander les paramètres de l'analyse
    print("\nCréation d'une nouvelle analyse de trafic:")
    query_name = input("Nom de la requête (laisser vide pour un nom automatique): ")
    days = input("Nombre de jours à analyser (défaut: 7): ")
    max_results = input("Nombre maximum de résultats (défaut: 1000): ")
    
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
        max_results = 1000
    else:
        try:
            max_results = int(max_results)
        except ValueError:
            print("Valeur invalide, utilisation de la valeur par défaut (1000).")
            max_results = 1000
    
    print("\nDémarrage de l'analyse de trafic...")
    start_time = time.time()
    
    # Créer une requête par défaut avec les paramètres spécifiés
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    api = IllumioAPI()
    traffic_op = TrafficAnalysisOperation(api=api)
    query_data = traffic_op.create_default_query(
        query_name=query_name or f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        start_date=start_date,
        end_date=end_date,
        max_results=max_results
    )
    
    # Exécuter l'analyse
    results = analyze_traffic(query_data=query_data)
    
    end_time = time.time()
    duration = end_time - start_time
    
    if results:
        print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
        print(f"   {len(results)} flux de trafic récupérés.")
    else:
        print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")

def view_traffic_analyses():
    """Affiche la liste des analyses de trafic existantes."""
    print("\nRécupération des analyses de trafic...")
    
    try:
        db = IllumioDatabase()
        queries = db.get_traffic_queries()
        
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
        db = IllumioDatabase()
        flows = db.get_traffic_flows(query_id)
        
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
        
        src_ip = flow.get('src_ip') or 'N/A'
        dst_ip = flow.get('dst_ip') or 'N/A'
        service = flow.get('service') or 'N/A'
        port = flow.get('port') or 'N/A'
        decision = flow.get('policy_decision') or 'N/A'
        
        print(f"{src_ip:<15} {dst_ip:<15} {service:<20} {port:<8} {decision:<15}")

def export_traffic_analysis():
    """Exporte les résultats d'une analyse de trafic."""
    print("\nRécupération des analyses de trafic...")
    
    try:
        db = IllumioDatabase()
        queries = db.get_traffic_queries()
        
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
        
        # Récupérer les flux
        flows = db.get_traffic_flows(query_id)
        
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
        if format_choice == 1:
            export_to_csv(flows, filename)
        elif format_choice == 2:
            export_to_json(flows, filename)
    
    except Exception as e:
        print(f"Erreur lors de l'export: {e}")

def export_to_csv(flows, filename):
    """Exporte les flux de trafic au format CSV."""
    import csv
    
    if not filename.endswith('.csv'):
        filename += '.csv'
    
    try:
        with open(filename, 'w', newline='') as csvfile:
            # Déterminer les en-têtes à partir des clés du premier flux
            fieldnames = [
                'src_ip', 'src_workload_id', 'dst_ip', 'dst_workload_id',
                'service', 'port', 'protocol', 'policy_decision',
                'first_detected', 'last_detected', 'num_connections', 'flow_direction'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for flow in flows:
                # Ne garder que les champs dans fieldnames
                filtered_flow = {k: flow.get(k) for k in fieldnames if k in flow}
                writer.writerow(filtered_flow)
        
        print(f"\n✅ Export CSV terminé. Fichier sauvegardé: {filename}")
    
    except Exception as e:
        print(f"Erreur lors de l'export CSV: {e}")

def export_to_json(flows, filename):
    """Exporte les flux de trafic au format JSON."""
    import json
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    try:
        with open(filename, 'w') as jsonfile:
            # Limiter les champs à exporter pour plus de lisibilité
            simplified_flows = []
            
            for flow in flows:
                simplified_flow = {
                    'src_ip': flow.get('src_ip'),
                    'src_workload_id': flow.get('src_workload_id'),
                    'dst_ip': flow.get('dst_ip'),
                    'dst_workload_id': flow.get('dst_workload_id'),
                    'service': flow.get('service'),
                    'port': flow.get('port'),
                    'protocol': flow.get('protocol'),
                    'policy_decision': flow.get('policy_decision'),
                    'first_detected': flow.get('first_detected'),
                    'last_detected': flow.get('last_detected'),
                    'num_connections': flow.get('num_connections'),
                    'flow_direction': flow.get('flow_direction')
                }
                simplified_flows.append(simplified_flow)
            
            json.dump(simplified_flows, jsonfile, indent=2)
        
        print(f"\n✅ Export JSON terminé. Fichier sauvegardé: {filename}")
    
    except Exception as e:
        print(f"Erreur lors de l'export JSON: {e}")