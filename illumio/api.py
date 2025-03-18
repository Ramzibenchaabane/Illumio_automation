import requests
import time
from urllib3.exceptions import InsecureRequestWarning
from .exceptions import APIRequestError, AuthenticationError, TimeoutError
from .utils import load_config

# Désactiver les avertissements pour les certificats auto-signés
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class IllumioAPI:
    """Classe principale pour interagir avec l'API Illumio."""
    
    def __init__(self, config_file='config/config.ini'):
        """Initialise la connexion à l'API Illumio en utilisant un fichier de configuration."""
        self.config = load_config(config_file)
        self.base_url = self.config.get('illumio', 'base_url')
        self.org_id = self.config.get('illumio', 'org_id')
        
        # Gérer la valeur booléenne manuellement
        verify_ssl = self.config.get('illumio', 'verify_ssl')
        self.session = requests.Session()
        self.session.verify = verify_ssl.lower() == 'true'
        
        # Headers par défaut
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Token CSRF à récupérer manuellement du navigateur
        self.csrf_token = self.config.get('illumio', 'csrf_token', fallback='')
        if self.csrf_token:
            self.session.headers.update({'X-CSRF-Token': self.csrf_token})
        
        # Cookie de session à récupérer manuellement du navigateur
        self.session_cookie = self.config.get('illumio', 'session_cookie', fallback='')
        if self.session_cookie:
            self.session.cookies.update({'JSESSIONID': self.session_cookie})
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Méthode générique pour faire des requêtes à l'API."""
        url = f"{self.base_url}/api/v2/orgs/{self.org_id}/{endpoint}"
        
        if params is None:
            params = {}
            
        try:
            if method.lower() == 'get':
                response = self.session.get(url, params=params)
            elif method.lower() == 'post':
                response = self.session.post(url, json=data, params=params)
            elif method.lower() == 'put':
                response = self.session.put(url, json=data)
            elif method.lower() == 'delete':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            if response.status_code == 401:
                raise AuthenticationError("Authentification échouée. Vérifiez les tokens d'authentification.")
            
            if response.status_code >= 400:
                raise APIRequestError(response.status_code, response.text)
            
            # Pour les requêtes qui ne retournent pas de contenu
            if response.status_code == 204:
                return True
            
            # Pour les requêtes qui retournent du contenu JSON
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise APIRequestError(0, str(e))
    
    def _make_paginated_request(self, method, endpoint, data=None, params=None):
        """Méthode pour faire des requêtes paginées à l'API et récupérer absolument TOUS les résultats."""
        if params is None:
            params = {}
        
        # Initialiser la liste des résultats
        all_results = []
        
        # Paramètres de pagination - utiliser la limite maximale supportée par l'API Illumio (500)
        if 'limit' not in params:
            params['limit'] = 500
        
        # Première requête sans offset
        print(f"  Récupération de la page 1 (limite: {params['limit']})...")
        response = self._make_request(method, endpoint, data, params)
        
        # Si la réponse n'est pas une liste, la retourner telle quelle
        if not isinstance(response, list):
            return response
        
        # Ajouter les résultats de la première page
        all_results.extend(response)
        print(f"  Éléments récupérés: {len(all_results)}")
        
        # Si la réponse est vide ou contient moins d'éléments que la limite, on a terminé
        if not response or len(response) < params['limit']:
            return all_results
        
        # Récupérer les pages suivantes avec pagination
        current_offset = params['limit']
        page = 2
        
        # Continuer à récupérer des pages tant qu'il y a des résultats
        while True:
            # Mettre à jour l'offset pour la prochaine page
            params_with_offset = params.copy()
            params_with_offset['offset'] = current_offset
            
            # Afficher la progression
            print(f"  Récupération de la page {page} (offset: {current_offset}, limite: {params['limit']})...")
            
            # Faire la requête pour la page suivante
            next_page = self._make_request(method, endpoint, data, params_with_offset)
            
            # Si la page est vide, on a terminé
            if not next_page or len(next_page) == 0:
                break
            
            # Ajouter les résultats de la page
            all_results.extend(next_page)
            print(f"  Total d'éléments récupérés: {len(all_results)}")
            
            # Si la page contient moins d'éléments que la limite, on a terminé
            if len(next_page) < params['limit']:
                break
            
            # Mettre à jour l'offset pour la prochaine page
            current_offset += len(next_page)
            page += 1
            
            # Pause courte pour éviter de surcharger l'API
            time.sleep(0.5)
        
        print(f"  Récupération terminée: {len(all_results)} éléments au total")
        return all_results
    
    def test_connection(self):
        """Teste la connexion au PCE Illumio."""
        try:
            self._make_request('get', 'labels')
            return True, "Connexion réussie"
        except AuthenticationError as e:
            return False, str(e)
        except APIRequestError as e:
            return False, f"Erreur API: {e}"
        except Exception as e:
            return False, f"Exception: {str(e)}"
    
    def get_workloads(self, params=None):
        """Récupère la liste complète des workloads avec filtres optionnels."""
        return self._make_paginated_request('get', 'workloads', params=params)
    
    def get_workload(self, workload_id):
        """Récupère les détails d'un workload spécifique."""
        return self._make_request('get', f'workloads/{workload_id}')
    
    def get_labels(self):
        """Récupère la liste complète des labels."""
        return self._make_paginated_request('get', 'labels')
    
    def get_ip_lists(self, pversion='draft', params=None):
        """Récupère la liste complète des IP lists.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        if params is None:
            params = {}
        
        # IMPORTANT: pversion est inclus dans le chemin, pas en tant que paramètre de requête
        endpoint = f"sec_policy/{pversion}/ip_lists"
        return self._make_paginated_request('get', endpoint, params=params)
    
    def get_services(self, pversion='draft', params=None):
        """Récupère la liste complète des services.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        if params is None:
            params = {}
        
        # IMPORTANT: pversion est inclus dans le chemin, pas en tant que paramètre de requête
        endpoint = f"sec_policy/{pversion}/services"
        return self._make_paginated_request('get', endpoint, params=params)
    
    def get_label_groups(self, pversion='draft', params=None):
        """Récupère la liste complète des groupes de labels.
        
        Args:
            pversion (str): Version de la politique ('draft' ou 'active'). Par défaut 'draft'.
            params (dict): Paramètres additionnels pour la requête.
        """
        if params is None:
            params = {}
        
        # IMPORTANT: pversion est inclus dans le chemin, pas en tant que paramètre de requête
        endpoint = f"sec_policy/{pversion}/label_groups"
        return self._make_paginated_request('get', endpoint, params=params)
    
    def get_label_dimensions(self):
        """Récupère les dimensions de labels disponibles."""
        return self._make_request('get', 'label_dimensions')
    
    def get_traffic_flows(self, params=None):
        """Récupère les flux de trafic avec filtres optionnels."""
        return self._make_paginated_request('get', 'traffic_flows', params=params)
    
    # Méthodes d'API pour les opérations asynchrones d'analyse de trafic
    
    def create_async_traffic_query(self, query_data):
        """Crée une requête asynchrone pour analyser les flux de trafic."""
        return self._make_request('post', 'traffic_flows/async_queries', data=query_data)
    
    def get_async_traffic_query_status(self, query_id):
        """Récupère le statut d'une requête asynchrone de trafic."""
        return self._make_request('get', f'traffic_flows/async_queries/{query_id}')
    
    def get_async_traffic_query_results(self, query_id):
        """Récupère les résultats d'une requête asynchrone de trafic."""
        return self._make_paginated_request('get', f'traffic_flows/async_queries/{query_id}/download')