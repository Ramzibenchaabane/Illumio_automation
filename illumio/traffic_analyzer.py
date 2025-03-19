# illumio/traffic_analyzer.py
"""
Module de gestion de l'analyse de trafic.
"""
import time
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List, Union, Tuple
from .api import IllumioAPI
from .database import IllumioDatabase
from .async_operations import TrafficAnalysisOperation
from .exceptions import ConfigurationError, APIRequestError, TimeoutError, AsyncOperationError

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
                status_callback: Optional[Callable[[str, Dict[str, Any], Optional[IllumioDatabase]], None]] = None,
                perform_deep_analysis=True, debug=False) -> Union[List[Dict[str, Any]], bool]:
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
            perform_deep_analysis (bool): Si True, effectue une analyse de règles approfondie après l'analyse de trafic
            debug (bool): Si True, affiche plus d'informations de débogage
            
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
            
            # Afficher la requête en mode debug
            if debug:
                print("\nDébug - Requête envoyée:")
                print(json.dumps(query_data, indent=2))
            
            # Stocker la requête dans la base de données avec un ID temporaire
            temp_id = "pending"
            if self.save_to_db:
                self.db.store_traffic_query(query_data, temp_id, status="created")
            
            # Soumettre la requête et obtenir l'ID
            query_id = traffic_op.submit(query_data)
            
            if not query_id:
                print("❌ Échec de soumission de la requête.")
                print("Vérifiez le format de votre requête et les journaux pour plus de détails.")
                return False
                
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
            
            # À CE STADE SEULEMENT, la première requête asynchrone est complétée
            # Stocker les résultats initiaux dans la base de données
            if self.save_to_db and query_id:
                print("Stockage des résultats initiaux dans la base de données...")
                if self.db.store_traffic_flows(query_id, results):
                    print("✅ Résultats initiaux stockés avec succès.")
                else:
                    print("❌ Erreur lors du stockage des résultats initiaux.")
            
            # Effectuer l'analyse de règles approfondie si demandé
            if perform_deep_analysis:
                print("\nLancement de l'analyse de règles approfondie...")
                deep_results = self._perform_deep_rule_analysis(query_id, polling_interval, max_attempts)
                
                if deep_results:
                    print(f"✅ Analyse de règles approfondie terminée avec {len(deep_results)} résultats.")
                    # Mettre à jour les résultats avec les informations de règles
                    results = deep_results
                    
                    # Stocker les résultats enrichis dans la base de données
                    if self.save_to_db and query_id:
                        print("Mise à jour des résultats avec les informations de règles...")
                        if self.db.store_traffic_flows(query_id, results):
                            print("✅ Résultats enrichis stockés avec succès.")
                        else:
                            print("❌ Erreur lors du stockage des résultats enrichis.")
                else:
                    print("⚠️ L'analyse de règles approfondie n'a pas abouti, utilisation des résultats de base.")
            
            return results
            
        except ConfigurationError as e:
            print(f"Erreur de configuration: {e}")
            return False
        except APIRequestError as e:
            print(f"Erreur API: {e}")
            if debug and query_data:
                print("\nDébug - Requête qui a causé l'erreur:")
                print(json.dumps(query_data, indent=2)[:1000]) # Afficher max 1000 caractères
            return False
        except TimeoutError as e:
            print(f"Erreur de délai d'attente: {e}")
            return False
        except Exception as e:
            print(f"Erreur inattendue: {e}")
            import traceback
            print(traceback.format_exc())
            return False
        
    def _perform_deep_rule_analysis(self, query_id: str, polling_interval: int = 5, max_attempts: int = 60) -> Union[List[Dict[str, Any]], None]:
        """
        Effectue une analyse de règles approfondie après une requête de trafic asynchrone.
        
        Args:
            query_id (str): ID de la requête de trafic terminée
            polling_interval (int): Intervalle en secondes entre les vérifications d'état
            max_attempts (int): Nombre maximal de tentatives de vérification
            
        Returns:
            list/None: Liste des résultats avec analyse de règles ou None si échec
        """
        try:
            # Vérifier d'abord que la requête de trafic initiale est bien terminée
            status_response = self.api._make_request('get', f'traffic_flows/async_queries/{query_id}')
            if status_response.get('status') != 'completed':
                print("❌ La requête de trafic initiale n'est pas encore terminée. Impossible de lancer l'analyse de règles.")
                return None
            
            # Étape 1: Lancer l'analyse de règles approfondie avec un appel PUT
            print("Démarrage de l'analyse de règles approfondie...")
            params = {'label_based_rules': 'false', 'offset': 0, 'limit': 100}
            
            try:
                # L'appel PUT retournera un code 202 sans contenu
                self.api._make_request('put', f'traffic_flows/async_queries/{query_id}/update_rules', params=params)
                print("✅ Requête d'analyse de règles approfondie acceptée.")
            except Exception as e:
                print(f"❌ Erreur lors du lancement de l'analyse de règles approfondie: {e}")
                return None
            
            # Mettre à jour le statut dans la base de données
            if self.save_to_db:
                self.db.update_traffic_query_rules_status(query_id, 'working')
            
            # Étape 2: Surveiller l'état de l'analyse de règles via des appels GET répétés
            print("Surveillance de l'état de l'analyse de règles...")
            
            attempts = 0
            rules_status = None
            
            while attempts < max_attempts:
                # Vérifier l'état actuel de la requête
                status_response = self.api._make_request('get', f'traffic_flows/async_queries/{query_id}')
                
                # Vérifier si l'attribut 'rules' est présent dans la réponse
                if 'rules' in status_response:
                    # Vérifier si rules est un dictionnaire
                    rules = status_response.get('rules')
                    
                    if isinstance(rules, dict) and 'status' in rules:
                        # Si rules est un dictionnaire et contient un attribut status
                        rules_status = rules.get('status')
                        
                        print(f"  État de l'analyse de règles: {rules_status} (tentative {attempts+1}/{max_attempts})")
                        
                        # Mettre à jour le statut dans la base de données
                        if self.save_to_db:
                            self.db.update_traffic_query_rules_status(query_id, rules_status)
                        
                        # Vérifier si l'analyse est terminée
                        if rules_status == 'completed':
                            print("Analyse de règles terminée avec succès.")
                            break
                    elif isinstance(rules, str):
                        # Si rules est une chaîne, utiliser directement cette valeur comme status
                        rules_status = rules
                        print(f"  État de l'analyse de règles: {rules_status} (tentative {attempts+1}/{max_attempts})")
                        
                        # Mettre à jour le statut dans la base de données
                        if self.save_to_db:
                            self.db.update_traffic_query_rules_status(query_id, rules_status)
                        
                        # Vérifier si l'analyse est terminée
                        if rules_status == 'completed':
                            print("Analyse de règles terminée avec succès.")
                            break
                    else:
                        print(f"  Format de 'rules' inattendu: {type(rules)} - {rules}")
                else:
                    print(f"  En attente du début de l'analyse de règles... (tentative {attempts+1}/{max_attempts})")
                
                # Attendre avant la prochaine vérification
                time.sleep(polling_interval)
                attempts += 1
            
            # Vérifier si l'analyse a été complétée
            if rules_status != 'completed':
                print(f"❌ L'analyse de règles n'a pas été complétée après {max_attempts} tentatives.")
                return None
            
            # Étape 3: Une fois que rules.status est "completed", récupérer les résultats finaux
            print("Récupération des résultats de l'analyse de règles...")
            download_params = {'offset': 0, 'limit': 5000}
            
            try:
                final_results = self.api._make_request(
                    'get', 
                    f'traffic_flows/async_queries/{query_id}/download',
                    params=download_params
                )
                print(f"✅ {len(final_results)} résultats récupérés avec analyse de règles.")
                return final_results
            except Exception as e:
                print(f"❌ Erreur lors de la récupération des résultats finaux: {e}")
                return None
                
        except APIRequestError as e:
            print(f"Erreur API lors de l'analyse de règles: {e}")
            return None
        except Exception as e:
            print(f"Erreur inattendue lors de l'analyse de règles: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
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
                # Si le flux est au format brut, extraire correctement les données
                if isinstance(flow.get('raw_data'), str):
                    try:
                        raw_data = json.loads(flow.get('raw_data', '{}'))
                        src = raw_data.get('src', {})
                        dst = raw_data.get('dst', {})
                        service = raw_data.get('service', {})
                        simplified_flow = {
                            'src_ip': src.get('ip'),
                            'src_workload_id': src.get('workload', {}).get('href', '').split('/')[-1] if src.get('workload', {}).get('href') else None,
                            'dst_ip': dst.get('ip'),
                            'dst_workload_id': dst.get('workload', {}).get('href', '').split('/')[-1] if dst.get('workload', {}).get('href') else None,
                            'service': service.get('name'),
                            'port': service.get('port'),
                            'protocol': service.get('proto'),
                            'policy_decision': raw_data.get('policy_decision'),
                            'first_detected': raw_data.get('timestamp_range', {}).get('first_detected'),
                            'last_detected': raw_data.get('timestamp_range', {}).get('last_detected'),
                            'num_connections': raw_data.get('num_connections'),
                            'flow_direction': raw_data.get('flow_direction'),
                            'rules': raw_data.get('rules')  # Ajout des règles issues de l'analyse approfondie
                        }
                    except json.JSONDecodeError:
                        # Si le décodage JSON échoue, utiliser les données directement
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
                            'flow_direction': flow.get('flow_direction'),
                            'rule_href': flow.get('rule_href'),
                            'rule_name': flow.get('rule_name')
                        }
                else:
                    # Si le flux n'est pas au format brut, utiliser directement les champs
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
                        'flow_direction': flow.get('flow_direction'),
                        'rule_href': flow.get('rule_href'),
                        'rule_name': flow.get('rule_name')
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
        import json
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        try:
            # Définir les en-têtes pour le CSV
            fieldnames = [
                'src_ip', 'src_workload_id', 'dst_ip', 'dst_workload_id',
                'service', 'port', 'protocol', 'policy_decision',
                'first_detected', 'last_detected', 'num_connections', 'flow_direction',
                'rule_href', 'rule_name'  # Ajout des informations de règles
            ]
            
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for flow in flows:
                    # Si le flux est au format brut, extraire correctement les données
                    if isinstance(flow.get('raw_data'), str):
                        try:
                            raw_data = json.loads(flow.get('raw_data', '{}'))
                            src = raw_data.get('src', {})
                            dst = raw_data.get('dst', {})
                            service = raw_data.get('service', {})
                            rules = raw_data.get('rules', {})
                            
                            # Extraire les informations de règles
                            rule_href = None
                            rule_name = None
                            if rules and 'sec_policy' in rules:
                                sec_policy = rules.get('sec_policy', {})
                                if sec_policy:
                                    rule_href = sec_policy.get('href')
                                    rule_name = sec_policy.get('name')
                            
                            csv_flow = {
                                'src_ip': src.get('ip'),
                                'src_workload_id': src.get('workload', {}).get('href', '').split('/')[-1] if src.get('workload', {}).get('href') else None,
                                'dst_ip': dst.get('ip'),
                                'dst_workload_id': dst.get('workload', {}).get('href', '').split('/')[-1] if dst.get('workload', {}).get('href') else None,
                                'service': service.get('name'),
                                'port': service.get('port'),
                                'protocol': service.get('proto'),
                                'policy_decision': raw_data.get('policy_decision'),
                                'first_detected': raw_data.get('timestamp_range', {}).get('first_detected'),
                                'last_detected': raw_data.get('timestamp_range', {}).get('last_detected'),
                                'num_connections': raw_data.get('num_connections'),
                                'flow_direction': raw_data.get('flow_direction'),
                                'rule_href': rule_href,
                                'rule_name': rule_name
                            }
                        except json.JSONDecodeError:
                            # Si le décodage JSON échoue, utiliser les données directement
                            csv_flow = {k: flow.get(k) for k in fieldnames if k in flow}
                    else:
                        # Si le flux n'est pas au format brut, utiliser directement les champs
                        csv_flow = {k: flow.get(k) for k in fieldnames if k in flow}
                    
                    writer.writerow(csv_flow)
            
            print(f"✅ Export CSV terminé. Fichier sauvegardé: {filename}")
            return True
        
        except Exception as e:
            print(f"Erreur lors de l'export CSV: {e}")
            return False