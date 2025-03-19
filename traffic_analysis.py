# traffic_analysis.py
#!/usr/bin/env python3
"""
Script pour l'analyse de trafic Illumio.
"""
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from illumio import (
    IllumioTrafficAnalyzer,
    ConfigurationError, 
    APIRequestError, 
    TimeoutError
)

def analyze_traffic(query_data=None, query_name=None, days=7, max_results=10000, save_to_db=True):
    """
    Exécute une analyse de trafic.
    
    Args:
        query_data (dict, optional): Données de requête personnalisées
        query_name (str, optional): Nom de la requête
        days (int): Nombre de jours à analyser
        max_results (int): Nombre maximum de résultats
        save_to_db (bool): Enregistrer les résultats dans la base de données
        
    Returns:
        list/bool: Résultats de l'analyse ou False si échec
    """
    # Calculer les dates pour l'analyse
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    date_range = (start_date, end_date)
    
    # Créer et utiliser l'analyseur de trafic
    analyzer = IllumioTrafficAnalyzer()
    return analyzer.analyze(
        query_data=query_data,
        query_name=query_name,
        date_range=date_range,
        max_results=max_results
    )

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Analyse de trafic Illumio')
    parser.add_argument('-n', '--name', help='Nom de la requête de trafic')
    parser.add_argument('-f', '--file', help='Fichier JSON contenant la requête de trafic')
    parser.add_argument('-o', '--output', help='Fichier de sortie pour les résultats (JSON)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Nombre de jours à analyser (par défaut: 7)')
    parser.add_argument('-m', '--max', type=int, default=10000, help='Nombre maximum de résultats (par défaut: 10000)')
    parser.add_argument('--no-db', action='store_true', help="Ne pas stocker les résultats dans la base de données")
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Format d\'export (par défaut: json)')
    parser.add_argument('--list', action='store_true', help='Lister les analyses de trafic existantes')
    parser.add_argument('--get', help='Récupérer les résultats d\'une analyse existante par ID')
    
    args = parser.parse_args()
    
    # Créer l'analyseur de trafic
    analyzer = IllumioTrafficAnalyzer()
    
    # Lister les analyses existantes
    if args.list:
        queries = analyzer.get_queries()
        if not queries:
            print("Aucune analyse de trafic trouvée.")
            return 0
        
        print(f"{len(queries)} analyses trouvées:\n")
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
        
        return 0
    
    # Récupérer les résultats d'une analyse existante
    if args.get:
        flows = analyzer.get_flows(args.get)
        if not flows:
            print(f"Aucun flux trouvé pour l'analyse {args.get}.")
            return 1
        
        print(f"{len(flows)} flux trouvés.")
        
        # Exporter si un fichier de sortie est spécifié
        if args.output:
            analyzer.export_flows(args.get, format_type=args.format, output_file=args.output)
        
        return 0
    
    print("=== Analyse de trafic Illumio ===")
    start_time = time.time()
    
    # Charger la requête depuis un fichier si spécifié
    query_data = None
    if args.file:
        try:
            with open(args.file, 'r') as f:
                query_data = json.load(f)
                print(f"Requête chargée depuis {args.file}")
        except Exception as e:
            print(f"Erreur lors du chargement du fichier de requête: {e}")
            return 1
    
    # Exécuter l'analyse de trafic
    results = analyze_traffic(
        query_data=query_data,
        query_name=args.name,
        days=args.days,
        max_results=args.max,
        save_to_db=not args.no_db
    )
    
    # Enregistrer les résultats dans un fichier si demandé
    if results and args.output:
        if isinstance(results, list):
            try:
                if args.format.lower() == 'json':
                    with open(args.output, 'w') as f:
                        json.dump(results, f, indent=2)
                elif args.format.lower() == 'csv':
                    import csv
                    fieldnames = [
                        'src', 'dst', 'service', 'policy_decision',
                        'num_connections', 'flow_direction'
                    ]
                    with open(args.output, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        for flow in results:
                            simplified_flow = {
                                'src': flow.get('src', {}).get('ip'),
                                'dst': flow.get('dst', {}).get('ip'),
                                'service': flow.get('service', {}).get('name'),
                                'policy_decision': flow.get('policy_decision'),
                                'num_connections': flow.get('num_connections'),
                                'flow_direction': flow.get('flow_direction')
                            }
                            writer.writerow(simplified_flow)
                
                print(f"Résultats enregistrés dans {args.output}")
            except Exception as e:
                print(f"Erreur lors de l'enregistrement des résultats: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\nDurée de l'analyse: {duration:.2f} secondes")
    
    return 0 if results else 1

if __name__ == "__main__":
    sys.exit(main())