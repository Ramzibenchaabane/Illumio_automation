# cli_modules/traffic_menu.py
#!/usr/bin/env python3
"""
Module de menu pour l'analyse de trafic Illumio.
"""
import time
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