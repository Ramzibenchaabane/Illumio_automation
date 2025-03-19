# illuminio/database/entity_manager/workload_manager.py
"""
Gestionnaire des workloads dans la base de données.
"""
import sqlite3
import json
from ...db_utils import db_connection

class WorkloadManager:
    """Gère les opérations de base de données pour les workloads."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire de workloads.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les workloads.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table Workloads
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS workloads (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    hostname TEXT,
                    description TEXT,
                    public_ip TEXT,
                    online INTEGER,
                    os_detail TEXT,
                    service_provider TEXT,
                    data_center TEXT,
                    data_center_zone TEXT,
                    enforcement_mode TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Table pour les relations entre Workloads et Labels
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS workload_labels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workload_id TEXT,
                    label_id TEXT,
                    FOREIGN KEY (workload_id) REFERENCES workloads (id),
                    FOREIGN KEY (label_id) REFERENCES labels (id)
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables workloads: {e}")
            return False
    
    def store(self, workloads):
        """Stocke les workloads dans la base de données.
        
        Args:
            workloads (list): Liste des workloads à stocker
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Vider la table des workloads-labels pour mise à jour
                cursor.execute("DELETE FROM workload_labels")
                
                for workload in workloads:
                    # Extraire l'ID depuis l'URL href
                    workload_id = workload.get('href', '').split('/')[-1] if workload.get('href') else None
                    
                    if not workload_id:
                        continue
                    
                    # Insérer ou mettre à jour le workload
                    cursor.execute('''
                    INSERT OR REPLACE INTO workloads 
                    (id, name, hostname, description, public_ip, online, os_detail, 
                    service_provider, data_center, data_center_zone, enforcement_mode, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        workload_id,
                        workload.get('name'),
                        workload.get('hostname'),
                        workload.get('description'),
                        workload.get('public_ip'),
                        1 if workload.get('online') else 0,
                        workload.get('os_detail'),
                        workload.get('service_provider'),
                        workload.get('data_center'),
                        workload.get('data_center_zone'),
                        workload.get('enforcement_mode', {}).get('mode') if isinstance(workload.get('enforcement_mode'), dict) else workload.get('enforcement_mode'),
                        json.dumps(workload)
                    ))
                    
                    # Lier les labels au workload
                    for label in workload.get('labels', []):
                        label_id = label.get('href', '').split('/')[-1] if label.get('href') else None
                        
                        if label_id:
                            cursor.execute('''
                            INSERT INTO workload_labels (workload_id, label_id)
                            VALUES (?, ?)
                            ''', (workload_id, label_id))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des workloads: {e}")
            return False
    
    def get(self, workload_id):
        """Récupère un workload par son ID.
        
        Args:
            workload_id (str): ID du workload à récupérer
            
        Returns:
            dict: Données du workload ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM workloads WHERE id = ?
                ''', (workload_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                return None
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du workload: {e}")
            return None
    
    def get_all(self):
        """Récupère tous les workloads.
        
        Returns:
            list: Liste des workloads
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM workloads
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des workloads: {e}")
            return []