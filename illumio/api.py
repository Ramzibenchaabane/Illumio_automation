# illumio/api.py
"""
Module principal pour interagir avec l'API Illumio.
Fournit des méthodes spécifiques pour chaque ressource Illumio.
"""
from .api_core import IllumioAPICore

class IllumioAPI(IllumioAPICore):
    """Classe principale pour interagir avec l'API Illumio."""
    
    def get_resource(self, resource_type, pversion=None, params=None):
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
        return self._make_async_request('get', endpoint, params=params)
    
    def get_workloads(self, params=None):
        """Récupère la liste des workloads avec filtres optionnels."""
        return self.get_resource('workloads', params=params)
    
    def get_workload(self, workload_id):
        """Récupère les détails d'un workload spécifique."""
        return self._make_request('get', f'workloads/{workload_id}')
    
    def get_labels(self, params=None):
        """Récupère la liste des labels."""
        return self.get_resource('labels', params=params)
    
    def get_ip_lists(self, pversion='draft', params=None):
        """
        Récupère la liste des IP lists.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        return self.get_resource('ip_lists', pversion=pversion, params=params)
    
    def get_services(self, pversion='draft', params=None):
        """
        Récupère la liste des services.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        return self.get_resource('services', pversion=pversion, params=params)
    
    def get_label_groups(self, pversion='draft', params=None):
        """
        Récupère la liste des groupes de labels.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        return self.get_resource('label_groups', pversion=pversion, params=params)
    
    def get_label_dimensions(self):
        """Récupère les dimensions de labels disponibles."""
        return self._make_request('get', 'label_dimensions')
    
    def get_traffic_flows(self, params=None):
        """Récupère les flux de trafic avec filtres optionnels."""
        return self._make_request('get', 'traffic_flows', params=params)
    
    # Méthodes d'API pour les opérations asynchrones d'analyse de trafic
    
    def create_async_traffic_query(self, query_data):
        """Crée une requête asynchrone pour analyser les flux de trafic."""
        return self._make_request('post', 'traffic_flows/async_queries', data=query_data)
    
    def get_async_traffic_query_status(self, query_id):
        """Récupère le statut d'une requête asynchrone de trafic."""
        return self._make_request('get', f'traffic_flows/async_queries/{query_id}')
    
    def get_async_traffic_query_results(self, query_id):
        """Récupère les résultats d'une requête asynchrone de trafic."""
        return self._make_request('get', f'traffic_flows/async_queries/{query_id}/download')