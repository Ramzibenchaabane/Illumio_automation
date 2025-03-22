# illumio/traffic_analysis/rule_analysis.py
"""
Handles deep rule analysis for traffic flows.
"""
import time
import random
from typing import Dict, Any, Optional, List, Union

from .base_components import TrafficAnalysisBaseComponent

# Importations pour les parseurs
from ..parsers.traffic_flow_parser import TrafficFlowParser
from ..parsers.rule_parser import RuleParser

# Importations pour les formatters
from ..formatters.rule_query_formatter import RuleQueryFormatter

class DeepRuleAnalyzer(TrafficAnalysisBaseComponent):
    """
    Performs in-depth analysis of security rules for traffic flows.
    """
    
    def perform_deep_rule_analysis(self, 
                                    query_id: str, 
                                    polling_interval: int = 5, 
                                    max_attempts: int = 60,
                                    label_based_rules: bool = False) -> Union[List[Dict[str, Any]], None]:
        """
        Perform a deep analysis of rules for a specific traffic query.
        
        Args:
            query_id (str): Unique identifier for the traffic query
            polling_interval (int): Time between status checks
            max_attempts (int): Maximum number of status check attempts
            label_based_rules (bool): Whether to use label-based rules
        
        Returns:
            List of traffic flows with detailed rule information or None
        """
        try:
            # Verify initial traffic query is completed
            status_response = self.api._make_request('get', f'traffic_flows/async_queries/{query_id}')
            if status_response.get('status') != 'completed':
                print(f"❌ La requête de trafic {query_id} n'est pas terminée. Impossible de lancer l'analyse de règles.")
                return None

            # Initiate deep rule analysis using formatter
            print("Démarrage de l'analyse de règles approfondie...")
            params = RuleQueryFormatter.format_rule_analysis_request(
                query_id=query_id,
                label_based_rules=label_based_rules,
                offset=0,
                limit=100
            )
            
            try:
                # PUT request to start rule analysis
                self.api._make_request('put', 
                                       f'traffic_flows/async_queries/{query_id}/update_rules', 
                                       params=params)
                print("✅ Requête d'analyse de règles approfondie acceptée.")
            except Exception as e:
                print(f"❌ Erreur lors du lancement de l'analyse de règles approfondie: {e}")
                return None
            
            # Update query rules status in database
            if self.save_to_db:
                try:
                    # Attendre un peu avant de mettre à jour le statut pour éviter les conflits
                    time.sleep(1)
                    
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            if self.db.update_traffic_query_rules_status(query_id, 'working'):
                                break
                            else:
                                if attempt < max_retries - 1:
                                    wait_time = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                                    print(f"Échec de mise à jour du statut des règles, tentative {attempt+1}/{max_retries} dans {wait_time:.2f}s...")
                                    time.sleep(wait_time)
                        except Exception as e:
                            if attempt < max_retries - 1:
                                wait_time = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                                print(f"Erreur lors de la mise à jour du statut des règles: {e}, tentative {attempt+1}/{max_retries} dans {wait_time:.2f}s...")
                                time.sleep(wait_time)
                            else:
                                print(f"Erreur lors de la mise à jour du statut des règles après plusieurs tentatives: {e}")
                except Exception as e:
                    print(f"Erreur lors du processus de retry: {e}")
            
            # Monitor rule analysis status
            print("Surveillance de l'état de l'analyse de règles...")
            
            attempts = 0
            rules_status = None
            
            while attempts < max_attempts:
                # Check current query status
                status_response = self.api._make_request('get', f'traffic_flows/async_queries/{query_id}')
                
                # Check for 'rules' attribute
                if 'rules' in status_response:
                    rules = status_response.get('rules')
                    
                    # Determine rules status
                    if isinstance(rules, dict) and 'status' in rules:
                        rules_status = rules.get('status')
                    elif isinstance(rules, str):
                        rules_status = rules
                    
                    print(f"  État de l'analyse de règles: {rules_status} (tentative {attempts+1}/{max_attempts})")
                    
                    # Update rules status in database
                    if self.save_to_db:
                        try:
                            # Use exponential backoff for database updates
                            max_db_retries = 5
                            for db_attempt in range(max_db_retries):
                                try:
                                    if self.db.update_traffic_query_rules_status(query_id, rules_status):
                                        break
                                    elif db_attempt < max_db_retries - 1:
                                        wait_time = (2 ** db_attempt) * 0.5 + random.uniform(0, 0.5)
                                        time.sleep(wait_time)
                                except Exception as e:
                                    if db_attempt < max_db_retries - 1:
                                        wait_time = (2 ** db_attempt) * 0.5 + random.uniform(0, 0.5)
                                        print(f"Erreur de base de données: {e}, tentative {db_attempt+1}/{max_db_retries} dans {wait_time:.2f}s...")
                                        time.sleep(wait_time)
                                    else:
                                        print(f"Erreur de base de données après plusieurs tentatives: {e}")
                        except Exception as e:
                            print(f"Erreur lors de la mise à jour du statut des règles: {e}")
                    
                    # Check if analysis is complete
                    if rules_status == 'completed':
                        print("Analyse de règles terminée avec succès.")
                        break
                else:
                    print(f"  En attente du début de l'analyse de règles... (tentative {attempts+1}/{max_attempts})")
                
                # Wait before next check
                time.sleep(polling_interval)
                attempts += 1
            
            # Check if rule analysis completed
            if rules_status != 'completed':
                print(f"❌ L'analyse de règles n'a pas été complétée après {max_attempts} tentatives.")
                return None
            
            # Attendre un peu pour s'assurer que les résultats sont disponibles
            time.sleep(2)
            
            # Retrieve final results using formatter for parameters
            print("Récupération des résultats de l'analyse de règles...")
            download_params = RuleQueryFormatter.format_rule_download_request(
                query_id=query_id,
                offset=0,
                limit=5000
            )
            
            try:
                raw_results = self.api._make_request(
                    'get', 
                    f'traffic_flows/async_queries/{query_id}/download',
                    params=download_params
                )
                
                # Parse les résultats en utilisant le parseur
                final_results = TrafficFlowParser.parse_flows(raw_results)
                
                print(f"✅ {len(final_results)} résultats récupérés avec analyse de règles.")
                return final_results
            except Exception as e:
                print(f"❌ Erreur lors de la récupération des résultats finaux: {e}")
                return None
                
        except Exception as e:
            print(f"Erreur inattendue lors de l'analyse de règles: {e}")
            import traceback
            print(traceback.format_exc())
            return None