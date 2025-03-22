# illumio/database/entity_managers/label_manager.py
"""
Gestionnaire des labels dans la base de données.
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional, Union, Tuple

from ...db_utils import db_connection
from ...converters.entity_converter import EntityConverter
from ...parsers.label_parser import LabelParser
from ...utils.response import ApiResponse, handle_exceptions


class LabelManager:
    """Gère les opérations de base de données pour les labels."""
    
    def __init__(self, db_file: str):
        """
        Initialise le gestionnaire de labels.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self) -> bool:
        """
        Initialise les tables nécessaires pour les labels.
        
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
                
                # Création d'index pour améliorer les performances
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_label_key_value ON labels(key, value)
                ''')
                
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables labels: {e}")
            return False
    
    @handle_exceptions
    def store(self, labels: List[Dict[str, Any]]) -> ApiResponse:
        """
        Stocke les labels dans la base de données.
        
        Args:
            labels (list): Liste des labels à stocker
            
        Returns:
            ApiResponse: Réponse indiquant le succès ou l'échec avec détails
        """
        with db_connection(self.db_file) as (conn, cursor):
            stored_count = 0
            
            for label_data in labels:
                # Nettoyer et normaliser le label via le parser
                label = LabelParser.parse_label(label_data)
                
                # Extraire l'ID
                label_id = label.get('id')
                if not label_id:
                    continue
                
                # Préparer les données pour l'insertion
                db_label = {
                    'id': label_id,
                    'key': label.get('key'),
                    'value': label.get('value'),
                    'raw_data': json.dumps(label) if isinstance(label, dict) else label.get('raw_data')
                }
                
                # Insérer ou mettre à jour le label
                query, params = EntityConverter.prepare_for_insert("labels", db_label)
                cursor.execute(query, params)
                stored_count += 1
        
        return ApiResponse.success(
            data={"stored_count": stored_count},
            message=f"{stored_count} labels stockés avec succès"
        )
    
    @handle_exceptions
    def get(self, label_id: str) -> ApiResponse:
        """
        Récupère un label par son ID.
        
        Args:
            label_id (str): ID du label à récupérer
            
        Returns:
            ApiResponse: Réponse contenant le label ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM labels WHERE id = ?
            ''', (label_id,))
            
            row = cursor.fetchone()
            if not row:
                return ApiResponse.error(
                    message=f"Label avec ID {label_id} non trouvé",
                    code=404
                )
            
            # Convertir l'enregistrement en dictionnaire
            label = dict(row)
            
            # Si raw_data est présent, l'extraire
            if 'raw_data' in label and isinstance(label['raw_data'], str):
                try:
                    raw_data = json.loads(label['raw_data'])
                    # Fusionner les données brutes avec l'entité
                    for key, value in raw_data.items():
                        if key not in label or label[key] is None:
                            label[key] = value
                except (json.JSONDecodeError, TypeError):
                    # Garder raw_data tel quel en cas d'erreur
                    pass
            
            return ApiResponse.success(
                data={"label": label}
            )
    
    @handle_exceptions
    def get_all(self) -> ApiResponse:
        """
        Récupère tous les labels.
        
        Returns:
            ApiResponse: Réponse contenant la liste des labels ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM labels
            ''')
            
            labels = []
            for row in cursor.fetchall():
                label = dict(row)
                
                # Traiter raw_data si présent
                if 'raw_data' in label and isinstance(label['raw_data'], str):
                    try:
                        label['parsed_data'] = json.loads(label['raw_data'])
                    except (json.JSONDecodeError, TypeError):
                        label['parsed_data'] = None
                
                labels.append(label)
            
            return ApiResponse.success(
                data={
                    "labels": labels,
                    "count": len(labels)
                }
            )
    
    @handle_exceptions
    def get_by_key(self, key: str) -> ApiResponse:
        """
        Récupère les labels par clé.
        
        Args:
            key (str): Clé des labels à récupérer
            
        Returns:
            ApiResponse: Réponse contenant la liste des labels ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM labels WHERE key = ?
            ''', (key,))
            
            labels = [dict(row) for row in cursor.fetchall()]
            
            return ApiResponse.success(
                data={
                    "labels": labels,
                    "count": len(labels)
                },
                message=f"{len(labels)} labels trouvés pour la clé '{key}'"
            )
    
    @handle_exceptions
    def get_by_key_value(self, key: str, value: str) -> ApiResponse:
        """
        Récupère un label par sa clé et sa valeur.
        
        Args:
            key (str): Clé du label
            value (str): Valeur du label
            
        Returns:
            ApiResponse: Réponse contenant le label ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM labels WHERE key = ? AND value = ?
            ''', (key, value))
            
            row = cursor.fetchone()
            if not row:
                return ApiResponse.error(
                    message=f"Label avec clé '{key}' et valeur '{value}' non trouvé",
                    code=404
                )
            
            label = dict(row)
            
            # Traiter raw_data si présent
            if 'raw_data' in label and isinstance(label['raw_data'], str):
                try:
                    label['parsed_data'] = json.loads(label['raw_data'])
                except (json.JSONDecodeError, TypeError):
                    label['parsed_data'] = None
            
            return ApiResponse.success(
                data={"label": label}
            )
    
    @handle_exceptions
    def delete(self, label_id: str) -> ApiResponse:
        """
        Supprime un label par son ID.
        
        Args:
            label_id (str): ID du label à supprimer
            
        Returns:
            ApiResponse: Réponse indiquant le succès ou l'échec
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Vérifier d'abord si le label est utilisé par des workloads
            cursor.execute('''
            SELECT COUNT(*) as count FROM workload_labels WHERE label_id = ?
            ''', (label_id,))
            
            result = cursor.fetchone()
            if result and result['count'] > 0:
                return ApiResponse.error(
                    message=f"Impossible de supprimer le label {label_id} car il est utilisé par {result['count']} workloads",
                    code=409
                )
            
            # Supprimer le label
            cursor.execute('''
            DELETE FROM labels WHERE id = ?
            ''', (label_id,))
            
            if cursor.rowcount > 0:
                return ApiResponse.success(
                    message=f"Label {label_id} supprimé avec succès"
                )
            else:
                return ApiResponse.error(
                    message=f"Label {label_id} non trouvé",
                    code=404
                )
    
    @handle_exceptions
    def get_dimensions(self) -> ApiResponse:
        """
        Récupère les dimensions de labels disponibles.
        
        Returns:
            ApiResponse: Réponse contenant les dimensions de labels
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Récupérer les clés uniques et le nombre de valeurs pour chaque clé
            cursor.execute('''
            SELECT key, COUNT(DISTINCT value) as value_count FROM labels
            GROUP BY key ORDER BY key
            ''')
            
            dimensions = []
            for row in cursor.fetchall():
                dimensions.append({
                    'key': row['key'],
                    'value_count': row['value_count']
                })
                
                # Récupérer les valeurs pour cette clé
                cursor.execute('''
                SELECT DISTINCT value FROM labels WHERE key = ? ORDER BY value
                ''', (row['key'],))
                
                values = [r['value'] for r in cursor.fetchall()]
                dimensions[-1]['values'] = values
            
            return ApiResponse.success(
                data={
                    "dimensions": dimensions,
                    "count": len(dimensions)
                }
            )