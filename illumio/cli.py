#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime, timedelta
from illumio import IllumioAPI, ConfigurationError, TrafficAnalysisOperation
from illumio.database import IllumioDatabase
from sync_data import sync_all_data
from traffic_analysis import analyze_traffic

def clear_screen():
    """Nettoie l'écran pour une meilleure lisibilité."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Affiche l'en-tête de l'application."""
    clear_screen()
    print("=" * 60)
    print("               ILLUMIO AUTOMATION TOOL               ")
    print("=" * 60)
    print()

def print_menu(options):
    """Affiche un menu avec des options numérotées."""
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    print("\n0. Quitter")
    print("-" * 60)

def get_user_choice(max_option):
    """Récupère le choix de l'utilisateur avec validation."""
    while True:
        try:
            choice = int(input("\nVotre choix: "))
            if 0 <= choice <= max_option:
                return choice
            print(f"Veuillez entrer un nombre entre 0 et {max_option}.")
        except ValueError:
            print("Veuillez entrer un nombre valide.")

def test_connection():
    """Teste la connexion à l'API Illumio et affiche le résultat."""
    print("\nTest de connexion à l'API Illumio...")
    try:
        api = IllumioAPI()
        success, message = api.test_connection()
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
    except ConfigurationError as e:
        print(f"❌ Erreur de configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def initialize_database():
    """Initialise la base de données si elle n'existe pas."""
    try:
        db = IllumioDatabase()
        db.init_db()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        return False

def sync_database_menu():
    """Menu pour la synchronisation de la base de données."""
    print_header()
    print("SYNCHRONISATION DE LA BASE DE DONNÉES\n")
    
    if not test_connection():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    if not initialize_database():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    print("\nOptions de synchronisation:")
    options = [
        "Synchroniser tous les éléments",
        "Synchroniser uniquement les workloads",
        "Synchroniser uniquement les labels",
        "Synchroniser uniquement les listes d'IPs",
        "Synchroniser uniquement les services",
        "Synchroniser uniquement les groupes de labels"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    start_time = time.time()
    
    if choice == 1:
        print("\nSynchronisation complète en cours...")
        success = sync_all_data()
    else:
        print("\nFonctionnalité non implémentée pour le moment.")
        # TODO: Implémenter les synchronisations partielles
        success = False
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        print(f"\n✅ Synchronisation terminée en {duration:.2f} secondes.")
    else:
        print(f"\n❌ Échec de la synchronisation après {duration:.2f} secondes.")
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

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
    
    elif choice == 2:
        view_traffic_analyses()
    
    elif choice == 3:
        export_traffic_analysis()
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

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
            limit = 20  # Limiter le nombre de flux à afficher
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
    
    except Exception as e:
        print(f"Erreur lors de la récupération des détails: {e}")

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

def main():
    """Fonction principale du CLI interactif."""
    # Vérifier si la base de données existe déjà
    db_file = 'data/illumio.db'
    db_exists = os.path.exists(db_file)
    
    # Afficher un message d'accueil
    print_header()
    print("Bienvenue dans l'outil d'automatisation Illumio!")
    print("\nCet outil vous permet de gérer et d'analyser votre environnement Illumio.")
    
    # Proposer de synchroniser la base de données au démarrage si elle n'existe pas
    if not db_exists:
        print("\nLa base de données locale n'a pas été détectée.")
        choice = input("Voulez-vous la synchroniser maintenant? (o/n): ").lower()
        if choice in ('o', 'oui', 'y', 'yes'):
            sync_database_menu()
    
    # Boucle principale du menu
    while True:
        print_header()
        print("MENU PRINCIPAL\n")
        
        main_options = [
            "Synchroniser la base de données",
            "Analyse de trafic",
            # Ajoutez ici d'autres options de menu au fur et à mesure
        ]
        
        print_menu(main_options)
        choice = get_user_choice(len(main_options))
        
        if choice == 0:
            print("\nMerci d'avoir utilisé l'outil d'automatisation Illumio. Au revoir!")
            return 0
        
        # Rediriger vers le sous-menu approprié
        if choice == 1:
            sync_database_menu()
        elif choice == 2:
            traffic_analysis_menu()
        # Ajoutez d'autres options ici au fur et à mesure

if __name__ == "__main__":
    sys.exit(main())