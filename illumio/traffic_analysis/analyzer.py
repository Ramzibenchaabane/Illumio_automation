# illumio/traffic_analysis/analyzer.py
"""
Main traffic analysis orchestration class.
"""
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union, List, Tuple

from .base_components import TrafficAnalysisBaseComponent
from .query_handler import TrafficQueryHandler
from .rule_analysis import DeepRuleAnalyzer
from .result_processing import TrafficResultProcessor
from .export_handler import TrafficExportHandler

from ..async_operations import TrafficAnalysisOperation
from ..exceptions import (
    ConfigurationError, 
    APIRequestError, 
    TimeoutError
)

class IllumioTrafficAnalyzer(TrafficAnalysisBaseComponent):
    """
    Comprehensive traffic analysis class that orchestrates 
    query creation, execution, and result processing.
    """
    
    def __init__(self, api=None, db=None):
        """
        Initialize the traffic analyzer with optional API and database instances.
        
        Args:
            api (IllumioAPI, optional): Illumio API instance
            db (IllumioDatabase, optional): Illumio Database instance
        """
        super().__init__(api, db)
        
        # Initialize component handlers
        self.query_handler = TrafficQueryHandler(self.api, self.db)
        self.rule_analyzer = DeepRuleAnalyzer(self.api, self.db)
        self.result_processor = TrafficResultProcessor()
        self.export_handler = TrafficExportHandler(self.api, self.db)
    
    def analyze(self, 
                query_data: Optional[Dict[str, Any]] = None, 
                query_name: Optional[str] = None, 
                date_range: Optional[Tuple[str, str]] = None,
                max_results: int = 10000, 
                polling_interval: int = 5,
                max_attempts: int = 60,
                status_callback: Optional[Callable] = None,
                perform_deep_analysis: bool = True,
                debug: bool = False) -> Union[List[Dict[str, Any]], bool]:
        """
        Execute a comprehensive traffic analysis.
        
        Args:
            query_data (dict, optional): Custom query configuration
            query_name (str, optional): Name for the analysis query
            date_range (tuple, optional): (start_date, end_date)
            max_results (int): Maximum number of results to retrieve
            polling_interval (int): Time between status checks
            max_attempts (int): Maximum status check attempts
            status_callback (callable, optional): Function to handle status updates
            perform_deep_analysis (bool): Whether to perform deep rule analysis
            debug (bool): Enable debug logging
        
        Returns:
            List of traffic flows or False if analysis fails
        """
        try:
            # Ensure database is initialized if saving is enabled
            if self.save_to_db:
                self.db.init_db()
            
            # Test API connection
            success, message = self.api.test_connection()
            if not success:
                print(f"❌ Connection failed: {message}")
                return False
            
            # Prepare query data
            if not query_data:
                # If no query data provided, create a default query
                start_date, end_date = date_range if date_range else (None, None)
                query_data = self.query_handler.create_default_query(
                    query_name=query_name,
                    start_date=start_date,
                    end_date=end_date,
                    max_results=max_results
                )
            
            # Store temporary query in database
            temp_id = "pending"
            if self.save_to_db:
                self.db.store_traffic_query(query_data, temp_id, status="created")
            
            # Prepare async operation
            traffic_op = TrafficAnalysisOperation(
                api=self.api,
                polling_interval=polling_interval,
                max_attempts=max_attempts,
                status_callback=lambda status, response: self._log_status_update(
                    status, response, status_callback
                )
            )
            
            # Submit and get query ID
            query_id = traffic_op.submit(query_data)
            if not query_id:
                print("❌ Query submission failed.")
                return False
            
            # Update query ID in database
            if self.save_to_db:
                # Attendre un peu avant de mettre à jour la base de données
                time.sleep(0.5)
                self.db.update_traffic_query_id(temp_id, query_id)
            
            # Execute the query and get results
            results = traffic_op.execute(query_data)
            
            if not results:
                print("❌ No results obtained.")
                return False
            
            print(f"✅ {len(results)} traffic flows retrieved.")
            
            # Store initial results in database
            if self.save_to_db and query_id:
                print("Storing initial results in database...")
                try:
                    # Attendre un peu avant de stocker les résultats
                    time.sleep(1)
                    
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            if self.db.store_traffic_flows(query_id, results):
                                print("✅ Initial results stored successfully.")
                                break
                            else:
                                if attempt < max_retries - 1:
                                    wait_time = (2 ** attempt) * 1.0 + random.uniform(0, 0.5)
                                    print(f"❌ Error storing initial results, retry {attempt+1}/{max_retries} in {wait_time:.2f}s...")
                                    time.sleep(wait_time)
                                else:
                                    print("❌ Error storing initial results after retries.")
                        except Exception as e:
                            if attempt < max_retries - 1:
                                wait_time = (2 ** attempt) * 1.0 + random.uniform(0, 0.5)
                                print(f"❌ Error storing initial results: {e}, retry {attempt+1}/{max_retries} in {wait_time:.2f}s...")
                                time.sleep(wait_time)
                            else:
                                print(f"❌ Error storing initial results after retries: {e}")
                except Exception as e:
                    print(f"❌ Error during retry process: {e}")
                    # Continue the process even if storage fails
            
            # Perform deep rule analysis if requested
            if perform_deep_analysis:
                print("\nLaunching deep rule analysis...")
                # Add a delay before starting deep rule analysis to avoid DB locks
                time.sleep(3)
                
                deep_results = self.rule_analyzer.perform_deep_rule_analysis(query_id)
                
                if deep_results:
                    print(f"✅ Deep rule analysis completed with {len(deep_results)} results.")
                    # Update results with rule information
                    results = deep_results
                    
                    # Store enriched results in database
                    if self.save_to_db and query_id:
                        print("Updating results with rule information...")
                        try:
                            # Attendre un peu avant de stocker les résultats enrichis
                            time.sleep(1)
                            
                            # Add a retry mechanism for database updates
                            max_retries = 5
                            for attempt in range(max_retries):
                                try:
                                    if self.db.store_traffic_flows(query_id, results):
                                        print("✅ Enriched results stored successfully.")
                                        break
                                    else:
                                        if attempt < max_retries - 1:
                                            wait_time = (2 ** attempt) * 1.0 + random.uniform(0, 0.5)
                                            print(f"❌ Error storing enriched results, retry {attempt+1}/{max_retries} in {wait_time:.2f}s...")
                                            time.sleep(wait_time)
                                        else:
                                            print("❌ Error storing enriched results after retries.")
                                except Exception as e:
                                    if attempt < max_retries - 1:
                                        wait_time = (2 ** attempt) * 1.0 + random.uniform(0, 0.5)
                                        print(f"❌ Error storing enriched results: {e}, retry {attempt+1}/{max_retries} in {wait_time:.2f}s...")
                                        time.sleep(wait_time)
                                    else:
                                        print(f"❌ Error storing enriched results after retries: {e}")
                        except Exception as e:
                            print(f"❌ Failed to store enriched results: {e}")
                            # Continue the process even if storage fails
                else:
                    print("⚠️ Deep rule analysis did not complete, using base results.")
            
            return results
        
        except ConfigurationError as e:
            print(f"Configuration Error: {e}")
            return False
        except APIRequestError as e:
            print(f"API Request Error: {e}")
            if debug and query_data:
                print("\nDebug - Query causing the error:")
                print(str(query_data)[:1000])  # Print first 1000 chars
            return False
        except TimeoutError as e:
            print(f"Timeout Error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected Error: {e}")
            import traceback
            print(traceback.format_exc())
            return False
    
def get_queries(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve existing traffic queries.
    
    Args:
        status (str, optional): Filter by query status
    
    Returns:
        List of traffic query details
    """
    if not self.save_to_db:
        print("Database is disabled, cannot retrieve queries.")
        return []
    
    try:
        # Récupérer les requêtes avec gestion d'erreur améliorée
        queries = self.db.get_traffic_queries(status)
        
        # Vérifier la structure des données retournées
        if queries is None:
            print("Attention: La méthode get_traffic_queries a retourné None")
            return []
            
        if not isinstance(queries, list):
            print(f"Attention: Le résultat n'est pas une liste mais un {type(queries)}")
            # Tenter de convertir en liste si possible
            if hasattr(queries, '__iter__'):
                queries = list(queries)
            else:
                queries = [queries] if queries else []
        
        return queries
    except Exception as e:
        import traceback
        print(f"Erreur lors de la récupération des requêtes: {e}")
        traceback.print_exc()
        return []

def get_flows(self, query_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve traffic flows for a specific query.
    
    Args:
        query_id (str): ID of the traffic query
    
    Returns:
        List of traffic flows
    """
    if not self.save_to_db:
        print("Database is disabled, cannot retrieve flows.")
        return []
    
    try:
        # Récupérer les flux avec gestion d'erreur améliorée
        flows = self.db.get_traffic_flows(query_id)
        
        # Vérifier la structure des données retournées
        if flows is None:
            print("Attention: La méthode get_traffic_flows a retourné None")
            return []
            
        if not isinstance(flows, list):
            print(f"Attention: Le résultat n'est pas une liste mais un {type(flows)}")
            # Tenter de convertir en liste si possible
            if hasattr(flows, '__iter__'):
                flows = list(flows)
            else:
                flows = [flows] if flows else []
        
        # Traitement supplémentaire pour s'assurer que les données brutes sont exploitables
        processed_flows = []
        for flow in flows:
            if isinstance(flow, dict) and 'raw_data' in flow and isinstance(flow['raw_data'], str):
                # Tenter de parser les données JSON stockées
                try:
                    import json
                    raw_data = json.loads(flow['raw_data'])
                    # Conserver le flux original mais ajouter les clés importantes pour le traitement
                    processed_flow = flow.copy()
                    
                    # N'ajouter que si les clés n'existent pas déjà dans le flow
                    if 'src' not in processed_flow and 'src' in raw_data:
                        processed_flow['src'] = raw_data['src']
                    if 'dst' not in processed_flow and 'dst' in raw_data:
                        processed_flow['dst'] = raw_data['dst']
                    if 'service' not in processed_flow and 'service' in raw_data:
                        processed_flow['service'] = raw_data['service']
                    if 'policy_decision' not in processed_flow and 'policy_decision' in raw_data:
                        processed_flow['policy_decision'] = raw_data['policy_decision']
                    if 'flow_direction' not in processed_flow and 'flow_direction' in raw_data:
                        processed_flow['flow_direction'] = raw_data['flow_direction']
                    if 'num_connections' not in processed_flow and 'num_connections' in raw_data:
                        processed_flow['num_connections'] = raw_data['num_connections']
                    if 'rules' not in processed_flow and 'rules' in raw_data:
                        processed_flow['rules'] = raw_data['rules']
                    
                    processed_flows.append(processed_flow)
                except Exception as e:
                    # En cas d'échec du parsing, conserver le flux original
                    processed_flows.append(flow)
            else:
                processed_flows.append(flow)
        
        return processed_flows
    except Exception as e:
        import traceback
        print(f"Erreur lors de la récupération des flux: {e}")
        traceback.print_exc()
        return []

def export_flows(self, 
                 query_id: str, 
                 format_type: str = 'json', 
                 output_file: Optional[str] = None) -> bool:
    """
    Export traffic flows for a specific query.
    
    Args:
        query_id (str): ID of the traffic query
        format_type (str): Export format ('json' or 'csv')
        output_file (str, optional): Custom output filename
    
    Returns:
        bool: True if export successful
    """
    if not self.save_to_db:
        print("Database is disabled, cannot export flows.")
        return False
    
    try:
        # Récupérer les flux avec la méthode améliorée
        flows = self.get_flows(query_id)
        
        if not flows:
            print(f"Aucun flux trouvé pour la requête {query_id}.")
            return False
        
        # Déléguer à l'export handler
        return self.export_handler.export_flows(
            flows, 
            output_file or f"traffic_analysis_{query_id}", 
            format_type
        )
    except Exception as e:
        import traceback
        print(f"Erreur lors de l'export des flux: {e}")
        traceback.print_exc()
        return False