#illumio/database/core.py
"""
Classe principale de gestion de la base de données SQLite.
"""
import os
import sqlite3
from ..db_utils import db_connection
from .entity_managers import (
    WorkloadManager, 
    LabelManager, 
    IPListManager, 
    ServiceManager, 
    LabelGroupManager
)
from .traffic_manager import TrafficManager
from .async_manager import AsyncOperationManager

class IllumioDatabase:
    """Gère la connexion et les opérations avec la base de données SQLite."""
    
    def __init__(self, db_file='data/illumio.db'):
        """Initialise la connexion à la base de données."""
        self.db_file = db_file
        # S'assurer que le dossier de la base de données existe
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        
        # Initialiser les gestionnaires
        self.workloads = WorkloadManager(db_file)
        self.labels = LabelManager(db_file)
        self.ip_lists = IPListManager(db_file)
        self.services = ServiceManager(db_file)
        self.label_groups = LabelGroupManager(db_file)
        self.traffic = TrafficManager(db_file)
        self.async_operations = AsyncOperationManager(db_file)
    
    def connect(self):
        """Établit la connexion à la base de données."""
        conn = sqlite3.connect(self.db_file)
        # Permettre d'accéder aux colonnes par nom
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor
    
    def close(self, conn):
        """Ferme la connexion à la base de données."""
        if conn:
            conn.close()
    
    def init_db(self):
        """Initialise la structure de la base de données."""
        try:
            # Initialiser les tables de base de données de chaque gestionnaire
            managers = [
                self.workloads,
                self.labels,
                self.ip_lists,
                self.services,
                self.label_groups,
                self.traffic,
                self.async_operations
            ]
            
            all_success = True
            for manager in managers:
                if not manager.init_tables():
                    all_success = False
            
            return all_success
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation de la base de données: {e}")
            return False
    
    # Méthodes de délégation pour maintenir la compatibilité avec le code existant
    def store_workloads(self, workloads):
        """Stocke les workloads dans la base de données."""
        return self.workloads.store(workloads)
    
    def store_labels(self, labels):
        """Stocke les labels dans la base de données."""
        return self.labels.store(labels)
    
    def store_ip_lists(self, ip_lists):
        """Stocke les listes d'IPs dans la base de données."""
        return self.ip_lists.store(ip_lists)
    
    def store_services(self, services):
        """Stocke les services dans la base de données."""
        return self.services.store(services)
    
    def store_label_groups(self, label_groups):
        """Stocke les groupes de labels dans la base de données."""
        return self.label_groups.store(label_groups)
    
    # Méthodes de délégation pour les opérations asynchrones
    def store_async_operation(self, operation_id, operation_type, status, data=None, result_id=None):
        """Stocke une opération asynchrone dans la base de données."""
        return self.async_operations.store(operation_id, operation_type, status, data, result_id)
    
    def update_async_operation_status(self, operation_id, status, error_message=None):
        """Met à jour le statut d'une opération asynchrone."""
        return self.async_operations.update_status(operation_id, status, error_message)
    
    def get_async_operation(self, operation_id):
        """Récupère les détails d'une opération asynchrone."""
        return self.async_operations.get(operation_id)
    
    def get_async_operations_by_type(self, operation_type, status=None):
        """Récupère les opérations asynchrones par type et statut optionnel."""
        return self.async_operations.get_by_type(operation_type, status)
    
    # Méthodes de délégation pour les requêtes de trafic
    def store_traffic_query(self, query_data, query_id, status='created'):
        """Stocke une requête de trafic asynchrone dans la base de données."""
        return self.traffic.store_query(query_data, query_id, status)
    
    def update_traffic_query_id(self, temp_id, new_id):
        """Met à jour l'ID d'une requête de trafic temporaire avec l'ID réel de l'API."""
        return self.traffic.update_query_id(temp_id, new_id)
    
    def update_traffic_query_status(self, query_id, status, rules_status=None):
        """Met à jour le statut d'une requête de trafic asynchrone."""
        return self.traffic.update_query_status(query_id, status, rules_status)
    
    def update_traffic_query_rules_status(self, query_id, rules_status):
        """Met à jour le statut des règles d'une requête de trafic asynchrone."""
        return self.traffic.update_query_rules_status(query_id, rules_status)
    
    def store_traffic_flows(self, query_id, flows):
        """Stocke les résultats d'une requête de trafic asynchrone."""
        return self.traffic.store_flows(query_id, flows)
    
    def get_traffic_queries(self, status=None):
        """Récupère les requêtes de trafic asynchrones avec filtre optionnel sur le statut."""
        return self.traffic.get_queries(status)
    
    def get_traffic_flows(self, query_id):
        """Récupère les flux de trafic pour une requête spécifique."""
        return self.traffic.get_flows(query_id)