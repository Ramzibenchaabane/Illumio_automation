# illumio/database/entity_manager/label_manager.py
"""
Gestionnaire des labels dans la base de données.
"""
import sqlite3
import json
from ...db_utils import db_connection

class LabelManager:
    """Gère les opérations de base de données pour les labels."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire de labels.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les labels.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table Labels
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS labels (
                    id TEXT PRIMARY KEY,
                    key TEXT,
                    value TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables labels: {e}")
            return False
    
    def store(self, labels):
        """Stocke les labels dans la base de données.
        
        Args:
            labels (list): Liste des labels à stocker
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                for label in labels:
                    # Extraire l'ID depuis l'URL href
                    label_id = label.get('href', '').split('/')[-1] if label.get('href') else None
                    
                    if not label_id:
                        continue
                    
                    # Insérer ou mettre à jour le label
                    cursor.execute('''
                    INSERT OR REPLACE INTO labels (id, key, value, raw_data)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        label_id,
                        label.get('key'),
                        label.get('value'),
                        json.dumps(label)
                    ))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des labels: {e}")
            return False
    
    def get(self, label_id):
        """Récupère un label par son ID.
        
        Args:
            label_id (str): ID du label à récupérer
            
        Returns:
            dict: Données du label ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM labels WHERE id = ?
                ''', (label_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                return None
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du label: {e}")
            return None
    
    def get_all(self):
        """Récupère tous les labels.
        
        Returns:
            list: Liste des labels
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM labels
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des labels: {e}")
            return []
    
    def get_by_key(self, key):
        """Récupère les labels par clé.
        
        Args:
            key (str): Clé des labels à récupérer
            
        Returns:
            list: Liste des labels correspondants
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM labels WHERE key = ?
                ''', (key,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des labels par clé: {e}")
            return []