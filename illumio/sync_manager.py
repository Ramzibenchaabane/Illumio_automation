# illumio/sync_manager.py
"""
Module de gestion de la synchronisation des données entre l'API Illumio et la base de données locale.
"""
import time
from typing import Dict, Any, List, Callable, Optional
from .api import IllumioAPI
from .database import IllumioDatabase
from .exceptions import IllumioAPIError, ConfigurationError, APIRequestError

class IllumioSyncManager:
    """Gère la synchronisation des données entre l'API Illumio et la base de données locale."""
    
    def __init__(self, api=None, db=None):
        """Initialise le gestionnaire de synchronisation."""
        self.api = api or IllumioAPI()
        self.db = db or IllumioDatabase()
        
        # Mapper les types de ressources aux méthodes de récupération et de stockage
        self.resource_map = {
            'workloads': {
                'fetch': self.api.get_workloads,
                'store': self.db.store_workloads,
                'name': 'workloads'
            },
            'labels': {
                'fetch': self.api.get_labels,
                'store': self.db.store_labels,
                'name': 'labels'
            },
            'ip_lists': {
                'fetch': self.api.get_ip_lists,
                'store': self.db.store_ip_lists,
                'name': 'listes d\'IPs'
            },
            'services': {
                'fetch': self.api.get_services,
                'store': self.db.store_services,
                'name': 'services'
            },
            'label_groups': {
                'fetch': self.api.get_label_groups,
                'store': self.db.store_label_groups,
                'name': 'groupes de labels'
            },
            'rule_sets': {
                'fetch': self.api.get_rule_sets,
                'store': self.db.store_rule_sets,
                'name': 'ensembles de règles'
            }
        }
    
    def sync_resource(self, resource_type: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Synchronise un type de ressource spécifique.
        
        Args:
            resource_type (str): Type de ressource à synchroniser (workloads, labels, etc.)
            params (dict, optional): Paramètres supplémentaires pour la requête
            
        Returns:
            bool: True si la synchronisation a réussi, False sinon
        """
        if resource_type not in self.resource_map:
            print(f"Type de ressource inconnu: {resource_type}")
            return False
        
        resource_info = self.resource_map[resource_type]
        fetch_method = resource_info['fetch']
        store_method = resource_info['store']
        name = resource_info['name']
        
        try:
            print(f"\nRécupération des {name} (mode asynchrone)...")
            data = fetch_method(params=params)
            
            if data and isinstance(data, list):
                print(f"✅ {len(data)} {name} récupérés.")
                
                print(f"Stockage des {name} dans la base de données...")
                if store_method(data):
                    print(f"✅ {name} stockés dans la base de données.")
                    return True
                else:
                    print(f"❌ Erreur lors du stockage des {name}.")
            else:
                print(f"❌ Échec de la récupération des {name}.")
            
            return False
        
        except (IllumioAPIError, Exception) as e:
            print(f"❌ Erreur lors de la synchronisation des {name}: {e}")
            return False
    
    def sync_all(self, params_map: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Synchronise tous les types de ressources.
        
        Args:
            params_map (dict, optional): Dictionnaire des paramètres pour chaque type de ressource
            
        Returns:
            bool: True si toutes les synchronisations ont réussi, False sinon
        """
        if params_map is None:
            params_map = {}
        
        # Initialiser la base de données
        print("Initialisation de la base de données...")
        if not self.db.init_db():
            print("Erreur lors de l'initialisation de la base de données.")
            return False
        
        # Test de connexion
        success, message = self.api.test_connection()
        if not success:
            print(f"Échec de la connexion: {message}")
            return False
        
        print(f"✅ {message}")
        
        # Synchroniser chaque type de ressource
        all_success = True
        for resource_type in self.resource_map.keys():
            params = params_map.get(resource_type, {})
            success = self.sync_resource(resource_type, params)
            all_success = all_success and success
        
        if all_success:
            print("\n✅ Synchronisation complète terminée avec succès.")
        else:
            print("\n⚠️ Synchronisation terminée avec des erreurs.")
        
        return all_success
    
    def sync_multiple(self, resource_types: List[str], params_map: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        Synchronise plusieurs types de ressources.
        
        Args:
            resource_types (list): Liste des types de ressources à synchroniser
            params_map (dict, optional): Dictionnaire des paramètres pour chaque type de ressource
            
        Returns:
            bool: True si toutes les synchronisations ont réussi, False sinon
        """
        if params_map is None:
            params_map = {}
        
        # Initialiser la base de données
        print("Initialisation de la base de données...")
        if not self.db.init_db():
            print("Erreur lors de l'initialisation de la base de données.")
            return False
        
        # Test de connexion
        success, message = self.api.test_connection()
        if not success:
            print(f"Échec de la connexion: {message}")
            return False
        
        print(f"✅ {message}")
        
        # Synchroniser chaque type de ressource demandé
        all_success = True
        for resource_type in resource_types:
            if resource_type in self.resource_map:
                params = params_map.get(resource_type, {})
                success = self.sync_resource(resource_type, params)
                all_success = all_success and success
            else:
                print(f"Type de ressource inconnu: {resource_type}")
                all_success = False
        
        if all_success:
            print("\n✅ Synchronisation terminée avec succès.")
        else:
            print("\n⚠️ Synchronisation terminée avec des erreurs.")
        
        return all_success