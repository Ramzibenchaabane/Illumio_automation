# illumio/api.py
"""
Module principal pour interagir avec l'API Illumio.
Fournit des méthodes spécifiques pour chaque ressource Illumio.
"""
from typing import Dict, List, Any, Optional, Union, Tuple

from .api_core import IllumioAPICore

# Importations des parseurs
from .parsers.api_response_parser import ApiResponseParser
from .parsers.traffic_flow_parser import TrafficFlowParser
from .parsers.rule_parser import RuleParser
from .parsers.workload_parser import WorkloadParser
from .parsers.label_parser import LabelParser
from .parsers.service_parser import ServiceParser
from .parsers.ip_list_parser import IPListParser

# Importations des formatters
from .formatters.rule_query_formatter import RuleQueryFormatter
from .formatters.traffic_query_formatter import TrafficQueryFormatter

class IllumioAPI(IllumioAPICore):
    """Classe principale pour interagir avec l'API Illumio."""
    
    def get_resource(self, resource_type: str, pversion: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Méthode générique pour récupérer une ressource avec pagination.
        
        Args:
            resource_type (str): Type de ressource (workloads, labels, etc.)
            pversion (str, optional): Version de la politique ('draft' ou 'active')
            params (dict, optional): Paramètres additionnels pour la requête
            
        Returns:
            Liste des ressources récupérées
        """
        if params is None:
            params = {}
        
        # Définir la limite par défaut
        if 'max_results' not in params:
            params['max_results'] = 10000
        
        # Construire l'endpoint
        if pversion:
            endpoint = f"sec_policy/{pversion}/{resource_type}"
        else:
            endpoint = resource_type
        
        # Faire la requête asynchrone
        response = self._make_async_request('get', endpoint, params=params)
        
        # Parser la réponse avec le parseur approprié
        return ApiResponseParser.parse_response(response)
    
    def get_workloads(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Récupère la liste des workloads avec filtres optionnels."""
        workloads = self.get_resource('workloads', params=params)
        # Parser les résultats pour les normaliser
        return WorkloadParser.parse_workloads(workloads)
    
    def get_workload(self, workload_id: str) -> Dict[str, Any]:
        """Récupère les détails d'un workload spécifique."""
        workload = self._make_request('get', f'workloads/{workload_id}')
        # Parser le résultat
        return WorkloadParser.parse_workload(workload)
    
    def get_labels(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Récupère la liste des labels."""
        labels = self.get_resource('labels', params=params)
        # Parser les résultats
        return LabelParser.parse_labels(labels)
    
    def get_ip_lists(self, pversion: str = 'draft', params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des IP lists.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        ip_lists = self.get_resource('ip_lists', pversion=pversion, params=params)
        # Parser les résultats
        return IPListParser.parse_ip_lists(ip_lists)
    
    def get_services(self, pversion: str = 'draft', params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des services.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        services = self.get_resource('services', pversion=pversion, params=params)
        # Parser les résultats
        return ServiceParser.parse_services(services)
    
    def get_label_groups(self, pversion: str = 'draft', params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des groupes de labels.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        label_groups = self.get_resource('label_groups', pversion=pversion, params=params)
        # Parser les résultats avec le parseur approprié (à créer si nécessaire)
        return label_groups
    
    def get_label_dimensions(self) -> List[Dict[str, Any]]:
        """Récupère les dimensions de labels disponibles."""
        dimensions = self._make_request('get', 'label_dimensions')
        # Parser les résultats
        return LabelParser.parse_label_dimensions(dimensions)
    
    def get_traffic_flows(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Récupère les flux de trafic avec filtres optionnels."""
        flows = self._make_request('get', 'traffic_flows', params=params)
        # Parser les résultats
        return TrafficFlowParser.parse_flows(flows)
    
    # Méthodes d'API pour les opérations asynchrones d'analyse de trafic
    
    def create_async_traffic_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée une requête asynchrone pour analyser les flux de trafic."""
        try:
            # Valider la requête en utilisant le formatter
            valid, message = TrafficQueryFormatter.validate_query(query_data)
            if not valid:
                print(f"AVERTISSEMENT: Requête invalide: {message}")
                # On continue quand même pour compatibilité
            
            response = self._make_request('post', 'traffic_flows/async_queries', data=query_data)
            if 'href' not in response:
                print(f"AVERTISSEMENT: La réponse de l'API ne contient pas d'attribut 'href'")
                print(f"Réponse complète: {response}")
            return response
        except Exception as e:
            print(f"Erreur lors de la création de la requête de trafic asynchrone: {e}")
            # Afficher une partie de la requête pour diagnostic
            import json
            print(f"Début de la requête envoyée: {json.dumps(query_data)[:200]}...")
            raise
    
    def get_async_traffic_query_status(self, query_id: str) -> Dict[str, Any]:
        """Récupère le statut d'une requête asynchrone de trafic."""
        response = self._make_request('get', f'traffic_flows/async_queries/{query_id}')
        # Parser la réponse avec le parseur API
        return ApiResponseParser.parse_response(response)
    
    def get_async_traffic_query_results(self, query_id: str) -> List[Dict[str, Any]]:
        """Récupère les résultats d'une requête asynchrone de trafic."""
        try:
            response = self._make_request('get', f'traffic_flows/async_queries/{query_id}/download')
            # Les résultats seront parsés par l'appelant
            return response
        except Exception as e:
            print(f"Erreur lors de la récupération des résultats (ID: {query_id}): {e}")
            # Essayer une autre approche si la première échoue
            print("Tentative alternative...")
            response = self._make_request('get', f'traffic_flows/async_queries/{query_id}/result')
            return response
    
    def start_deep_rule_analysis(self, query_id: str, label_based_rules: bool = False, offset: int = 0, limit: int = 100) -> bool:
        """
        Lance une analyse de règles approfondie sur une requête de trafic existante.
        
        Args:
            query_id (str): ID de la requête de trafic
            label_based_rules (bool): Si True, utilise les règles basées sur les labels
            offset (int): Index de départ pour les résultats
            limit (int): Nombre maximum de résultats
            
        Returns:
            bool: True si la requête a été acceptée, False sinon
        """
        try:
            # Préparer les paramètres en utilisant le formatter
            params = RuleQueryFormatter.format_rule_analysis_request(
                query_id=query_id,
                label_based_rules=label_based_rules,
                offset=offset,
                limit=limit
            )
            
            # Faire la requête PUT pour lancer l'analyse de règles
            # Cette requête retourne un code 202 sans contenu, donc nous traitons cela comme un succès
            try:
                self._make_request('put', f'traffic_flows/async_queries/{query_id}/update_rules', params=params)
                return True  # Si aucune exception n'est levée, considérer que la requête a été acceptée
            except Exception as e:
                # Vérifier si l'exception est due à un "succès sans contenu" (code 202)
                if hasattr(e, 'status_code') and e.status_code == 202:
                    return True
                raise  # Relever l'exception si ce n'est pas un code 202
                
        except Exception as e:
            print(f"Erreur lors du lancement de l'analyse de règles approfondie: {e}")
            return False
    
    def get_deep_rule_analysis_results(self, query_id: str, offset: int = 0, limit: int = 5000) -> List[Dict[str, Any]]:
        """
        Récupère les résultats d'une analyse de règles approfondie.
        
        Args:
            query_id (str): ID de la requête de trafic
            offset (int): Index de départ pour les résultats
            limit (int): Nombre maximum de résultats
            
        Returns:
            list: Liste des flux de trafic avec analyse de règles
        """
        # Utiliser le formatter pour les paramètres
        params = RuleQueryFormatter.format_rule_download_request(
            query_id=query_id,
            offset=offset,
            limit=limit
        )
        
        response = self._make_request('get', f'traffic_flows/async_queries/{query_id}/download', params=params)
        # Les résultats seront parsés par l'appelant
        return response
    
    def get_rule_sets(self, pversion: str = 'draft', params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des rule sets.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
            
        Returns:
            list: Liste des rule sets avec leurs règles
        """
        rule_sets = self.get_resource('rule_sets', pversion=pversion, params=params)
        # Parser les résultats
        return RuleParser.parse_rule_sets(rule_sets) if hasattr(RuleParser, 'parse_rule_sets') else rule_sets

    def get_rule_set(self, rule_set_id: str, pversion: str = 'draft') -> Dict[str, Any]:
        """
        Récupère les détails d'un rule set spécifique.
        
        Args:
            rule_set_id (str): ID du rule set
            pversion (str): Version de la politique ('draft' ou 'active')
            
        Returns:
            dict: Détails du rule set et ses règles
        """
        rule_set = self._make_request('get', f'sec_policy/{pversion}/rule_sets/{rule_set_id}')
        # Parser le résultat
        return RuleParser.parse_rule_set(rule_set) if hasattr(RuleParser, 'parse_rule_set') else rule_set

    def get_rule(self, rule_set_id: str, rule_id: str, pversion: str = 'draft') -> Dict[str, Any]:
        """
        Récupère les détails d'une règle spécifique.
        
        Args:
            rule_set_id (str): ID du rule set parent
            rule_id (str): ID de la règle
            pversion (str): Version de la politique ('draft' ou 'active')
            
        Returns:
            dict: Détails de la règle
        """
        rule = self._make_request('get', f'sec_policy/{pversion}/rule_sets/{rule_set_id}/sec_rules/{rule_id}')
        # Parser le résultat
        return RuleParser.parse_rule(rule)

    def get_rule_by_href(self, rule_href: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails d'une règle à partir de son href complet.
        
        Args:
            rule_href (str): Href complet de la règle (par exemple /api/v2/orgs/1/sec_policy/active/rule_sets/123/sec_rules/456)
            
        Returns:
            dict: Détails de la règle ou None si non trouvée
        """
        # Extraire les composants du href en utilisant le parseur API
        components = rule_href.split('/')
        
        # Vérifier si le href a le bon format
        if len(components) < 10 or components[-4] != 'rule_sets' or components[-2] != 'sec_rules':
            print(f"Format de href invalide: {rule_href}")
            return None
        
        # Extraire la version de la politique (draft ou active)
        pversion = components[-6]
        # Extraire l'ID du rule set
        rule_set_id = components[-3]
        # Extraire l'ID de la règle
        rule_id = components[-1]
        
        # Appeler l'API pour récupérer la règle
        try:
            rule = self.get_rule(rule_set_id, rule_id, pversion)
            return rule
        except Exception as e:
            print(f"Erreur lors de la récupération de la règle {rule_id}: {e}")
            return None