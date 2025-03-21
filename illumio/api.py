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
        # CORRECTION: Pas de doublon dans l'affichage
        try:
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
    
    def get_async_traffic_query_status(self, query_id):
        """Récupère le statut d'une requête asynchrone de trafic."""
        return self._make_request('get', f'traffic_flows/async_queries/{query_id}')
    
    def get_async_traffic_query_results(self, query_id):
        """Récupère les résultats d'une requête asynchrone de trafic."""
        try:
            return self._make_request('get', f'traffic_flows/async_queries/{query_id}/download')
        except Exception as e:
            print(f"Erreur lors de la récupération des résultats (ID: {query_id}): {e}")
            # Essayer une autre approche si la première échoue
            print("Tentative alternative...")
            return self._make_request('get', f'traffic_flows/async_queries/{query_id}/result')
    
    def start_deep_rule_analysis(self, query_id, label_based_rules=False, offset=0, limit=100):
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
            # Préparer les paramètres
            params = {
                'label_based_rules': 'true' if label_based_rules else 'false', 
                'offset': offset, 
                'limit': limit
            }
            
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
    
    def get_deep_rule_analysis_results(self, query_id, offset=0, limit=5000):
        """
        Récupère les résultats d'une analyse de règles approfondie.
        
        Args:
            query_id (str): ID de la requête de trafic
            offset (int): Index de départ pour les résultats
            limit (int): Nombre maximum de résultats
            
        Returns:
            list: Liste des flux de trafic avec analyse de règles
        """
        params = {'offset': offset, 'limit': limit}
        return self._make_request('get', f'traffic_flows/async_queries/{query_id}/download', params=params)
    
    def get_rule_sets(self, pversion='draft', params=None):
        """
        Récupère la liste des rule sets.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
            
        Returns:
            list: Liste des rule sets avec leurs règles
        """
        return self.get_resource('rule_sets', pversion=pversion, params=params)

    def get_rule_set(self, rule_set_id, pversion='draft'):
        """
        Récupère les détails d'un rule set spécifique.
        
        Args:
            rule_set_id (str): ID du rule set
            pversion (str): Version de la politique ('draft' ou 'active')
            
        Returns:
            dict: Détails du rule set et ses règles
        """
        return self._make_request('get', f'sec_policy/{pversion}/rule_sets/{rule_set_id}')

    def get_rule(self, rule_set_id, rule_id, pversion='draft'):
        """
        Récupère les détails d'une règle spécifique.
        
        Args:
            rule_set_id (str): ID du rule set parent
            rule_id (str): ID de la règle
            pversion (str): Version de la politique ('draft' ou 'active')
            
        Returns:
            dict: Détails de la règle
        """
        return self._make_request('get', f'sec_policy/{pversion}/rule_sets/{rule_set_id}/sec_rules/{rule_id}')

    def get_rule_by_href(self, rule_href):
        """
        Récupère les détails d'une règle à partir de son href complet.
        
        Args:
            rule_href (str): Href complet de la règle (par exemple /api/v2/orgs/1/sec_policy/active/rule_sets/123/sec_rules/456)
            
        Returns:
            dict: Détails de la règle
        """
        # Extraire les composants du href
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
            return self.get_rule(rule_set_id, rule_id, pversion)
        except Exception as e:
            print(f"Erreur lors de la récupération de la règle {rule_id}: {e}")
            return None