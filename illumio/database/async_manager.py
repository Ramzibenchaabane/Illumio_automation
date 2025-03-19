"""
Gestionnaire des opérations asynchrones dans la base de données.
"""
import sqlite3
import json
from ..db_utils import db_connection

class AsyncOperationManager:
    """Gère les opérations de base de données pour les opérations asynchrones."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire d'opérations asynchrones.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les opérations asynchrones.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table pour les opérations asynchrones génériques
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS async_operations (
                    id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data TEXT,
                    result_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables d'opérations asynchrones: {e}")
            return False
    
    def store(self, operation_id, operation_type, status, data=None, result_id=None):
        """Stocke une opération asynchrone dans la base de données.
        
        Args:
            operation_id (str): ID de l'opération
            operation_type (str): Type d'opération (ex: traffic_analysis)
            status (str): Statut initial de l'opération
            data (dict, optional): Données associées à l'opération
            result_id (str, optional): ID du résultat si applicable
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                INSERT OR REPLACE INTO async_operations 
                (id, operation_type, status, data, result_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    operation_id,
                    operation_type,
                    status,
                    json.dumps(data) if data else None,
                    result_id
                ))
                
            return True
            
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage de l'opération asynchrone: {e}")
            return False
    
    def update_status(self, operation_id, status, error_message=None):
        """Met à jour le statut d'une opération asynchrone.
        
        Args:
            operation_id (str): ID de l'opération
            status (str): Nouveau statut
            error_message (str, optional): Message d'erreur en cas d'échec
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Définir la date de complétion si l'opération est terminée
                if status in ["completed", "failed"]:
                    cursor.execute('''
                    UPDATE async_operations
                    SET status = ?, updated_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                    ''', (status, error_message, operation_id))
                else:
                    cursor.execute('''
                    UPDATE async_operations
                    SET status = ?, updated_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                    ''', (status, error_message, operation_id))
            
            return True
            
        except sqlite3.Error as e:
            print(f"Erreur lors de la mise à jour du statut de l'opération: {e}")
            return False
    
    def get(self, operation_id):
        """Récupère les détails d'une opération asynchrone.
        
        Args:
            operation_id (str): ID de l'opération
            
        Returns:
            dict: Détails de l'opération ou None si non trouvée
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM async_operations WHERE id = ?
                ''', (operation_id,))
                
                row = cursor.fetchone()
                if row:
                    # Convertir les données JSON si présentes
                    result = dict(row)
                    if result.get('data'):
                        result['data'] = json.loads(result['data'])
                    return result
                
                return None
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération de l'opération asynchrone: {e}")
            return None
    
    def get_by_type(self, operation_type, status=None):
        """Récupère les opérations asynchrones par type et statut optionnel.
        
        Args:
            operation_type (str): Type d'opération
            status (str, optional): Filtre sur le statut
            
        Returns:
            list: Liste des opérations correspondantes
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                if status:
                    cursor.execute('''
                    SELECT * FROM async_operations 
                    WHERE operation_type = ? AND status = ?
                    ORDER BY created_at DESC
                    ''', (operation_type, status))
                else:
                    cursor.execute('''
                    SELECT * FROM async_operations 
                    WHERE operation_type = ?
                    ORDER BY created_at DESC
                    ''', (operation_type,))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('data'):
                        result['data'] = json.loads(result['data'])
                    results.append(result)
                
                return results
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des opérations asynchrones: {e}")
            return []
    
    def delete(self, operation_id):
        """Supprime une opération asynchrone.
        
        Args:
            operation_id (str): ID de l'opération à supprimer
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                DELETE FROM async_operations WHERE id = ?
                ''', (operation_id,))
                
                return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la suppression de l'opération: {e}")
            return False
    
    def clean_old_operations(self, days_threshold=30):
        """Nettoie les opérations anciennes terminées.
        
        Args:
            days_threshold (int): Nombre de jours avant suppression
            
        Returns:
            int: Nombre d'opérations supprimées
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                DELETE FROM async_operations 
                WHERE status IN ('completed', 'failed') 
                AND completed_at < datetime('now', '-? days')
                ''', (days_threshold,))
                
                return cursor.rowcount
                
        except sqlite3.Error as e:
            print(f"Erreur lors du nettoyage des anciennes opérations: {e}")
            return 0