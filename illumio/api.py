import requests
from urllib3.exceptions import InsecureRequestWarning
from .exceptions import APIRequestError, AuthenticationError
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
        """Récupère la liste des workloads avec filtres optionnels."""
        return self._make_request('get', 'workloads', params=params)
    
    def get_workload(self, workload_id):
        """Récupère les détails d'un workload spécifique."""
        return self._make_request('get', f'workloads/{workload_id}')
    
    def get_labels(self):
        """Récupère la liste des labels."""
        return self._make_request('get', 'labels')
    
    def get_ip_lists(self):
        """Récupère la liste des IP lists."""
        return self._make_request('get', 'sec_policy/ip_lists')
    # Ajouter ces méthodes à la classe IllumioAPI

def get_services(self):
    """Récupère la liste des services."""
    return self._make_request('get', 'sec_policy/services')

def get_label_groups(self):
    """Récupère la liste des groupes de labels."""
    return self._make_request('get', 'sec_policy/label_groups')

def get_label_dimensions(self):
    """Récupère les dimensions de labels disponibles."""
    return self._make_request('get', 'label_dimensions')

def get_traffic_flows(self, params=None):
    """Récupère les flux de trafic avec filtres optionnels."""
    return self._make_request('get', 'traffic_flows', params=params)

def create_async_traffic_query(self, query_data):
    """Crée une requête asynchrone pour analyser les flux de trafic."""
    return self._make_request('post', 'traffic_flows/async_queries', data=query_data)

def get_async_traffic_query_status(self, query_id):
    """Récupère le statut d'une requête asynchrone de trafic."""
    return self._make_request('get', f'traffic_flows/async_queries/{query_id}')

def get_async_traffic_query_results(self, query_id):
    """Récupère les résultats d'une requête asynchrone de trafic."""
    return self._make_request('get', f'traffic_flows/async_queries/{query_id}/download')