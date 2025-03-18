#!/usr/bin/env python3
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from illumio import IllumioAPI, ConfigurationError, APIRequestError, TimeoutError
from illumio.database import IllumioDatabase

def create_default_query(query_name, max_results=1000):
    """Crée une requête de trafic par défaut."""
    # Définir les dates par défaut (7 derniers jours)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Structure de base d'une requête de trafic
    return {
        "query_name": query_name,
        "start_date": start_date,
        "end_date": end_date,
        "sources_destinations_query_op": "and",
        "sources": {
            "include": [
                {"actors": "ams"}  # All Managed Systems
            ],
            "exclude": []
        },
        "destinations": {
            "include": [
                {"actors": "ams"}  # All Managed Systems
            ],
            "exclude": []
        },
        "services": {
            "include": [],
            "exclude": []
        },
        "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
        "max_results": max_results,
        "exclude_workloads_from_ip_list_query": True
    }

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
        
        # Utiliser la requête fournie ou créer une requête par défaut
        if not query_data:
            # Générer un nom de requête par défaut si non fourni
            if not query_name:
                query_name = f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            query_data = create_default_query(query_name)
        
        print(f"\nSoumission de la requête de trafic '{query_data.get('query_name')}'...")
        
        # Soumettre la requête
        query_response = api.create_async_traffic_query(query_data)
        query_id = query_response.get('id')
        
        if not query_id:
            print("❌ Impossible d'obtenir l'ID de la requête asynchrone.")
            return False
        
        print(f"✅ Requête soumise avec l'ID: {query_id}")
        
        # Stocker la requête dans la base de données
        if db:
            db.store_traffic_query(query_data, query_id)
        
        # Surveiller le statut de la requête
        print("\nSurveillance du statut de la requête...")
        progress_chars = ['|', '/', '-', '\\']
        attempts = 0
        
        status = None
        while attempts < max_attempts:
            try:
                status_response = api.get_async_traffic_query_status(query_id)
                new_status = status_response.get('status')
                
                # Mise à jour du statut si changé
                if new_status != status:
                    status = new_status
                    print(f"Statut: {status}")
                    
                    if db:
                        db.update_traffic_query_status(query_id, status)
                
                # Vérifier si la requête est terminée
                if status == 'completed':
                    print("✅ Requête terminée avec succès!")
                    break
                elif status == 'failed':
                    error_message = status_response.get('error_message', 'Raison inconnue')
                    print(f"❌ La requête a échoué: {error_message}")
                    return False
                
                # Afficher un indicateur de progression
                progress_char = progress_chars[attempts % len(progress_chars)]
                print(f"\rAttente... {progress_char}", end='')
                sys.stdout.flush()
                
                # Attendre avant la prochaine vérification
                time.sleep(polling_interval)
                attempts += 1
                
            except APIRequestError as e:
                print(f"\n❌ Erreur lors de la vérification du statut: {e}")
                return False
        
        if attempts >= max_attempts:
            print(f"\n❌ Délai d'attente dépassé après {max_attempts * polling_interval} secondes.")
            return False
        
        # Récupérer les résultats
        print("\nRécupération des résultats...")
        results = api.get_async_traffic_query_results(query_id)
        
        if not results:
            print("❌ Aucun résultat obtenu.")
            return False
        
        print(f"✅ {len(results)} flux de trafic récupérés.")
        
        # Stocker les résultats dans la base de données
        if db:
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

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Analyse de trafic Illumio')
    parser.add_argument('-n', '--name', help='Nom de la requête de trafic')
    parser.add_argument('-f', '--file', help='Fichier JSON contenant la requête de trafic')
    parser.add_argument('-o', '--output', help='Fichier de sortie pour les résultats (JSON)')
    parser.add_argument('-d', '--days', type=int, default=7, help='Nombre de jours à analyser (par défaut: 7)')
    parser.add_argument('-m', '--max', type=int, default=1000, help='Nombre maximum de résultats (par défaut: 1000)')
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
    
    return 0 if results else 1

if __name__ == "__main__":
    sys.exit(main())