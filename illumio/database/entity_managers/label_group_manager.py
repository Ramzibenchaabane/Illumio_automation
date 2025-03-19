"""
Gestionnaire des groupes de labels dans la base de données.
"""
import sqlite3
import json
from ...db_utils import db_connection

class LabelGroupManager:
    """Gère les opérations de base de données pour les groupes de labels."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire de groupes de labels.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les groupes de labels.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table Label Groups
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS label_groups (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Table pour les relations entre Label Groups et Labels
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS label_group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label_group_id TEXT,
                    label_id TEXT,
                    FOREIGN KEY (label_group_id) REFERENCES label_groups (id),
                    FOREIGN KEY (label_id) REFERENCES labels (id)
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables des groupes de labels: {e}")
            return False
    
    def store(self, label_groups):
        """Stocke les groupes de labels dans la base de données.
        
        Args:
            label_groups (list): Liste des groupes de labels à stocker
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Vider la table des membres de groupe pour mise à jour
                cursor.execute("DELETE FROM label_group_members")
                
                for label_group in label_groups:
                    # Extraire l'ID depuis l'URL href
                    label_group_id = label_group.get('href', '').split('/')[-1] if label_group.get('href') else None
                    
                    if not label_group_id:
                        continue
                    
                    # Insérer ou mettre à jour le groupe de labels
                    cursor.execute('''
                    INSERT OR REPLACE INTO label_groups (id, name, description, raw_data)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        label_group_id,
                        label_group.get('name'),
                        label_group.get('description'),
                        json.dumps(label_group)
                    ))
                    
                    # Insérer les membres du groupe
                    for member in label_group.get('sub_groups', []):
                        member_id = member.get('href', '').split('/')[-1] if member.get('href') else None
                        
                        if member_id:
                            cursor.execute('''
                            INSERT INTO label_group_members (label_group_id, label_id)
                            VALUES (?, ?)
                            ''', (label_group_id, member_id))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des groupes de labels: {e}")
            return False
    
    def get(self, label_group_id):
        """Récupère un groupe de labels par son ID avec ses membres.
        
        Args:
            label_group_id (str): ID du groupe de labels à récupérer
            
        Returns:
            dict: Données du groupe de labels ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Récupérer le groupe de labels
                cursor.execute('''
                SELECT * FROM label_groups WHERE id = ?
                ''', (label_group_id,))
                
                group_row = cursor.fetchone()
                if not group_row:
                    return None
                
                group = dict(group_row)
                
                # Récupérer les membres du groupe
                cursor.execute('''
                SELECT l.* FROM labels l
                JOIN label_group_members lgm ON l.id = lgm.label_id
                WHERE lgm.label_group_id = ?
                ''', (label_group_id,))
                
                group['members'] = [dict(row) for row in cursor.fetchall()]
                
                return group
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du groupe de labels: {e}")
            return None
    
    def get_all(self):
        """Récupère tous les groupes de labels.
        
        Returns:
            list: Liste des groupes de labels
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM label_groups
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des groupes de labels: {e}")
            return []
    
    def get_members(self, label_group_id):
        """Récupère les membres d'un groupe de labels.
        
        Args:
            label_group_id (str): ID du groupe de labels
            
        Returns:
            list: Liste des labels membres du groupe
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT l.* FROM labels l
                JOIN label_group_members lgm ON l.id = lgm.label_id
                WHERE lgm.label_group_id = ?
                ''', (label_group_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des membres du groupe: {e}")
            return []