#traffic_analysis.py
#!/usr/bin/env python3
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from illumio import (
    IllumioAPI, 
    ConfigurationError, 
    APIRequestError, 
    TimeoutError, 
    TrafficAnalysisOperation
)
from illumio.database import IllumioDatabase

def analyze_traffic(query_data=None, query_name=None, save_to_db=True, polling_interval=5, max_attempts=60):
    """Exécute une analyse de trafic et stocke les résultats dans la base de données."""
    try:
        # Initialiser l'API et la base de données
        api = IllumioAPI()
        db = IllumioDatabase() if save_to_db else None
        
        # Initialiser la base de données si nécessaire
        if db:
            db.init_db()
        
        # Test de connexion
        success, message = api.test_connection()
        if not success:
            print(f"Échec de la connexion: {message}")
            return False
        
        print(f"✅ {message}")
        
        # Créer une instance d'opération d'analyse de trafic
        traffic_op = TrafficAnalysisOperation(
            api=api,
            polling_interval=polling_interval,
            max_attempts=max_attempts,
            status_callback=lambda status, response: on_status_update(status, response, db)
        )
        
        # Utiliser la requête fournie ou créer une requête par défaut
        if not query_data:
            # Générer un nom de requête par défaut si non fourni
            if not query_name:
                query_name = f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            query_data = traffic_op.create_default_query(query_name)
        
        print(f"\nSoumission de la requête de trafic '{query_data.get('query_name')}'...")
        
        # Stocker la requête dans la base de données
        if db:
            db.store_traffic_query(query_data, "pending", status="created")
        
        # Soumettre la requête et obtenir l'ID
        query_id = traffic_op.submit(query_data)
        print(f"✅ Requête soumise avec l'ID: {query_id}")
        
        # Mettre à jour l'ID dans la base de données
        if db and query_id:
            db.update_traffic_query_id("pending", query_id)
        
        print("\nSurveillance du statut de la requête...")
        
        # Exécuter l'opération asynchrone avec surveillance
        results = traffic_op.execute(query_data)
        
        if not results:
            print("❌ Aucun résultat obtenu.")
            return False
        
        print(f"✅ {len(results)} flux de trafic récupérés.")
        
        # Stocker les résultats dans la base de données
        if db and query_id:
            print("Stockage des résultats dans la base de données...")
            if db.store_traffic_flows(query_id, results):
                print("✅ Résultats stockés avec succès.")
            else:
                print("❌ Erreur lors du stockage des résultats.")
        
        return results
        
    except ConfigurationError as e:
        print(f"Erreur de configuration: {e}")
        return False
    except APIRequestError as e:
        print(f"Erreur API: {e}")
        return False
    except TimeoutError as e:
        print(f"Erreur de délai d'attente: {e}")
        return False
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False

def on_status_update(status, response, db=None):
    """Fonction de rappel pour les mises à jour d'état des requêtes asynchrones."""
    query_id = response.get('id')
    print(f"Statut de la requête {query_id}: {status}")
    
    # Indicateur de progression visuel
    progress_chars = ['|', '/', '-', '\\']
    progress_char = progress_chars[hash(status) % len(progress_chars)]
    print(f"{progress_char} ", end='')
    sys.stdout.flush()
    
    # Mettre à jour l'état dans la base de données
    if db and query_id:
        db.update_traffic_query_status(query_id, status)

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Analyse de trafic Illumio')
    parser.add_argument('-n', '--name', help='Nom de la requête de trafic')
    parser.add_argument('-f', '--file', help='Fichier JSON contenant la requête de trafic')
    parser.add_argument('-o', '--output', help='Fichier de sortie pour les résultats (JSON)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Nombre de jours à analyser (par défaut: 7)')
    parser.add_argument('-m', '--max', type=int, default=10000, help='Nombre maximum de résultats (par défaut: 10000)')
    parser.add_argument('--no-db', action='store_true', help="Ne pas stocker les résultats dans la base de données")
    
    args = parser.parse_args()
    
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
        save_to_db=not args.no_db
    )
    
    # Enregistrer les résultats dans un fichier si demandé
    if results and args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
                print(f"Résultats enregistrés dans {args.output}")
        except Exception as e:
            print(f"Erreur lors de l'enregistrement des résultats: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\nDurée de l'analyse: {duration:.2f} secondes")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())