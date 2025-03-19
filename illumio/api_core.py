# illumio/api_core.py
"""
Module de base pour l'API Illumio contenant les fonctionnalités fondamentales
de communication avec l'API REST d'Illumio.
"""
import requests
import time
from urllib3.exceptions import InsecureRequestWarning
from .exceptions import APIRequestError, AuthenticationError, TimeoutError, AsyncOperationError
from .utils import load_config

# Désactiver les avertissements pour les certificats auto-signés
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class IllumioAPICore:
    """Classe fondamentale pour la communication avec l'API Illumio."""
    
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
    
    def _make_async_request(self, method, endpoint, data=None, params=None, polling_interval=5, max_attempts=60):
        """
        Effectue une requête asynchrone générique.
        
        Args:
            method (str): Méthode HTTP (GET, POST, etc.)
            endpoint (str): Point d'accès de l'API
            data (dict, optional): Données à envoyer pour POST/PUT
            params (dict, optional): Paramètres de requête
            polling_interval (int): Intervalle en secondes entre les vérifications d'état
            max_attempts (int): Nombre maximal de tentatives de vérification
            
        Returns:
            Les résultats de l'opération asynchrone
            
        Raises:
            AsyncOperationError: Si l'opération asynchrone échoue
            TimeoutError: Si l'opération n'est pas terminée dans le délai imparti
        """
        if params is None:
            params = {}
        
        # Ajouter les paramètres spécifiques pour une requête asynchrone
        async_params = params.copy()
        async_params['async'] = 'true'  # Indiquer que nous voulons une opération asynchrone
        
        print(f"Démarrage d'une requête asynchrone pour l'endpoint {endpoint}...")
        
        # Soumission de la requête asynchrone
        response = self._make_request(method, endpoint, data, async_params)
        
        # Vérifier si la réponse contient un ID d'opération
        if not isinstance(response, dict) or 'href' not in response:
            # Si l'API ne retourne pas d'identifiant d'opération asynchrone, 
            # c'est qu'elle a peut-être traité la requête de manière synchrone
            return response
        
        # Extraire l'ID de l'opération asynchrone de la réponse
        operation_href = response['href']
        operation_id = operation_href.split('/')[-1]
        
        print(f"Opération asynchrone démarrée avec l'ID: {operation_id}")
        print("Surveillance de l'état de l'opération...")
        
        # Suivre l'état de l'opération asynchrone
        attempts = 0
        while attempts < max_attempts:
            # Récupérer l'état actuel de l'opération
            status_response = self._make_request('get', f"async_queries/{operation_id}")
            
            status = status_response.get('status')
            print(f"  État de l'opération asynchrone: {status} (tentative {attempts+1}/{max_attempts})")
            
            # Vérifier si l'opération est terminée
            if status == 'completed':
                print("Opération terminée avec succès, récupération des résultats...")
                # Récupérer les résultats
                results = self._make_request('get', f"async_queries/{operation_id}/download")
                return results
            elif status in ['failed', 'error']:
                error_message = status_response.get('error_message', 'Raison inconnue')
                raise AsyncOperationError(operation_id, status, error_message)
            
            # Attendre avant la prochaine vérification
            time.sleep(polling_interval)
            attempts += 1
        
        # Si on arrive ici, c'est que l'opération a expiré
        raise TimeoutError(f"L'opération asynchrone n'a pas été complétée après {max_attempts * polling_interval} secondes")
    
    def test_connection(self):
        """Teste la connexion au PCE Illumio."""
        try:
            self._make_request('get', 'labels', params={'max_results': 1})
            return True, "Connexion réussie"
        except AuthenticationError as e:
            return False, str(e)
        except APIRequestError as e:
            return False, f"Erreur API: {e}"
        except Exception as e:
            return False, f"Exception: {str(e)}"