# illumio/traffic_analyzer.py
"""
Module de gestion de l'analyse de trafic.
"""
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List, Union
from .api import IllumioAPI
from .database import IllumioDatabase
from .async_operations import TrafficAnalysisOperation
from .exceptions import ConfigurationError, APIRequestError, TimeoutError

class IllumioTrafficAnalyzer:
    """Gère l'analyse de trafic avec l'API Illumio."""
    
    def __init__(self, api=None, db=None):
        """Initialise l'analyseur de trafic."""
        self.api = api or IllumioAPI()
        self.db = db
        
        # Par défaut, la base de données est activée, mais peut être désactivée
        if db is None:
            self.db = IllumioDatabase()
            self.save_to_db = True
        else:
            self.db = db
            self.save_to_db = bool(db)  # Si db est None, save_to_db sera False
    
    def analyze(self, query_data=None, query_name=None, date_range=None, 
                max_results=10000, polling_interval=5, max_attempts=60,
                status_callback: Optional[Callable[[str, Dict[str, Any], Optional[IllumioDatabase]], None]] = None) -> Union[List[Dict[str, Any]], bool]:
        """
        Exécute une analyse de trafic et stocke les résultats dans la base de données.
        
        Args:
            query_data (dict, optional): Données de requête personnalisées, si None une requête par défaut sera créée
            query_name (str, optional): Nom de la requête, si None un nom par défaut sera généré
            date_range (tuple, optional): Tuple (date_début, date_fin) au format 'YYYY-MM-DD'
            max_results (int): Nombre maximum de résultats (défaut: 10000)
            polling_interval (int): Intervalle en secondes entre les vérifications d'état
            max_attempts (int): Nombre maximal de tentatives de vérification
            status_callback (callable, optional): Fonction de rappel pour recevoir les mises à jour d'état
            
        Returns:
            list/bool: Liste des flux de trafic ou False si échec
        """
        try:
            # Initialiser la base de données si nécessaire
            if self.save_to_db:
                self.db.init_db()
            
            # Test de connexion
            success, message = self.api.test_connection()
            if not success:
                print(f"Échec de la connexion: {message}")
                return False
            
            print(f"✅ {message}")
            
            # Créer une instance d'opération d'analyse de trafic
            traffic_op = TrafficAnalysisOperation(
                api=self.api,
                polling_interval=polling_interval,
                max_attempts=max_attempts,
                status_callback=lambda status, response: self._on_status_update(status, response, status_callback)
            )
            
            # Utiliser la requête fournie ou créer une requête par défaut
            if not query_data:
                # Générer un nom de requête par défaut si non fourni
                if not query_name:
                    query_name = f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Créer les dates par défaut si non fournies
                if not date_range:
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                else:
                    start_date, end_date = date_range
                
                query_data = traffic_op.create_default_query(
                    query_name=query_name,
                    start_date=start_date,
                    end_date=end_date,
                    max_results=max_results
                )
            
            print(f"\nSoumission de la requête de trafic '{query_data.get('query_name')}'...")
            
            # Stocker la requête dans la base de données avec un ID temporaire
            temp_id = "pending"
            if self.save_to_db:
                self.db.store_traffic_query(query_data, temp_id, status="created")
            
            # Soumettre la requête et obtenir l'ID
            query_id = traffic_op.submit(query_data)
            print(f"✅ Requête soumise avec l'ID: {query_id}")
            
            # Mettre à jour l'ID dans la base de données
            if self.save_to_db and query_id:
                self.db.update_traffic_query_id(temp_id, query_id)
            
            print("\nSurveillance du statut de la requête...")
            
            # Exécuter l'opération asynchrone avec surveillance
            results = traffic_op.execute(query_data)
            
            if not results:
                print("❌ Aucun résultat obtenu.")
                return False
            
            print(f"✅ {len(results)} flux de trafic récupérés.")
            
            # Stocker les résultats dans la base de données
            if self.save_to_db and query_id:
                print("Stockage des résultats dans la base de données...")
                if self.db.store_traffic_flows(query_id, results):
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
    
    def _on_status_update(self, status: str, response: Dict[str, Any], 
                         external_callback: Optional[Callable[[str, Dict[str, Any], Optional[IllumioDatabase]], None]] = None) -> None:
        """
        Gère les mises à jour d'état des requêtes asynchrones.
        
        Args:
            status (str): Statut actuel de l'opération
            response (dict): Réponse complète contenant les détails du statut
            external_callback (callable, optional): Fonction de rappel externe à appeler
        """
        query_id = response.get('id')
        print(f"Statut de la requête {query_id}: {status}")
        
        # Indicateur de progression visuel
        progress_chars = ['|', '/', '-', '\\']
        progress_char = progress_chars[hash(status) % len(progress_chars)]
        print(f"{progress_char} ", end='')
        sys.stdout.flush()
        
        # Mettre à jour l'état dans la base de données
        if self.save_to_db and query_id:
            self.db.update_traffic_query_status(query_id, status)
        
        # Appeler le callback externe si fourni
        if external_callback:
            external_callback(status, response, self.db if self.save_to_db else None)
    
    def get_queries(self, status=None):
        """
        Récupère les requêtes de trafic existantes.
        
        Args:
            status (str, optional): Filtre par statut
            
        Returns:
            list: Liste des requêtes de trafic
        """
        if not self.save_to_db:
            print("Base de données désactivée, impossible de récupérer les requêtes.")
            return []
        
        return self.db.get_traffic_queries(status)
    
    def get_flows(self, query_id):
        """
        Récupère les flux de trafic pour une requête spécifique.
        
        Args:
            query_id (str): ID de la requête
            
        Returns:
            list: Liste des flux de trafic
        """
        if not self.save_to_db:
            print("Base de données désactivée, impossible de récupérer les flux.")
            return []
        
        return self.db.get_traffic_flows(query_id)
    
    def export_flows(self, query_id, format_type='json', output_file=None):
        """
        Exporte les flux de trafic dans différents formats.
        
        Args:
            query_id (str): ID de la requête
            format_type (str): Format d'export ('json', 'csv')
            output_file (str, optional): Nom du fichier de sortie
            
        Returns:
            bool: True si l'export a réussi, False sinon
        """
        if not self.save_to_db:
            print("Base de données désactivée, impossible d'exporter les flux.")
            return False
        
        flows = self.db.get_traffic_flows(query_id)
        if not flows:
            print(f"Aucun flux trouvé pour la requête {query_id}.")
            return False
        
        # Définir le nom de fichier par défaut si non fourni
        if not output_file:
            output_file = f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}"
        
        # Exporter selon le format demandé
        try:
            if format_type.lower() == 'json':
                return self._export_to_json(flows, output_file)
            elif format_type.lower() == 'csv':
                return self._export_to_csv(flows, output_file)
            else:
                print(f"Format non supporté: {format_type}")
                return False
        except Exception as e:
            print(f"Erreur lors de l'export: {e}")
            return False
    
    def _export_to_json(self, flows, filename):
        """
        Exporte les flux au format JSON.
        
        Args:
            flows (list): Liste des flux à exporter
            filename (str): Nom du fichier de sortie
            
        Returns:
            bool: True si l'export a réussi, False sinon
        """
        import json
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            # Simplifier les données pour l'export
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
            
            with open(filename, 'w') as f:
                json.dump(simplified_flows, f, indent=2)
            
            print(f"✅ Export JSON terminé. Fichier sauvegardé: {filename}")
            return True
        
        except Exception as e:
            print(f"Erreur lors de l'export JSON: {e}")
            return False
    
    def _export_to_csv(self, flows, filename):
        """
        Exporte les flux au format CSV.
        
        Args:
            flows (list): Liste des flux à exporter
            filename (str): Nom du fichier de sortie
            
        Returns:
            bool: True si l'export a réussi, False sinon
        """
        import csv
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        try:
            # Définir les en-têtes pour le CSV
            fieldnames = [
                'src_ip', 'src_workload_id', 'dst_ip', 'dst_workload_id',
                'service', 'port', 'protocol', 'policy_decision',
                'first_detected', 'last_detected', 'num_connections', 'flow_direction'
            ]
            
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for flow in flows:
                    # Ne garder que les champs définis dans fieldnames
                    filtered_flow = {k: flow.get(k) for k in fieldnames if k in flow}
                    writer.writerow(filtered_flow)
            
            print(f"✅ Export CSV terminé. Fichier sauvegardé: {filename}")
            return True
        
        except Exception as e:
            print(f"Erreur lors de l'export CSV: {e}")
            return False