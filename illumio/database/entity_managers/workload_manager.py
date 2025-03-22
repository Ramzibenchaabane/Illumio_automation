# illumio/database/entity_managers/workload_manager.py
"""
Gestionnaire des workloads dans la base de données.
"""
import sqlite3
from typing import List, Dict, Any, Optional, Union, Tuple

from ...db_utils import db_connection
from ...converters.workload_converter import WorkloadConverter
from ...converters.entity_converter import EntityConverter
from ...models.workload import Workload
from ...utils.response import ApiResponse, handle_exceptions


class WorkloadManager:
    """Gère les opérations de base de données pour les workloads."""
    
    def __init__(self, db_file: str):
        """
        Initialise le gestionnaire de workloads.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self) -> bool:
        """
        Initialise les tables nécessaires pour les workloads.
        
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
                
                # Table pour les interfaces de Workloads
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS workload_interfaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workload_id TEXT,
                    name TEXT,
                    address TEXT,
                    link_state TEXT,
                    addresses TEXT,
                    FOREIGN KEY (workload_id) REFERENCES workloads (id)
                )
                ''')
                
                # Ajouter des index pour améliorer les performances
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_workload_hostname ON workloads(hostname)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_workload_labels ON workload_labels(workload_id, label_id)
                ''')
                
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables workloads: {e}")
            return False
    
    @handle_exceptions
    def store(self, workloads: List[Dict[str, Any]]) -> ApiResponse:
        """
        Stocke les workloads dans la base de données.
        
        Args:
            workloads (list): Liste des workloads à stocker
            
        Returns:
            ApiResponse: Réponse indiquant le succès ou l'échec avec détails
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Vider la table des workloads-labels pour mise à jour
            cursor.execute("DELETE FROM workload_labels")
            # Vider la table des interfaces pour mise à jour
            cursor.execute("DELETE FROM workload_interfaces")
            
            stored_count = 0
            for workload_data in workloads:
                # Convertir le workload pour la base de données
                db_workload = WorkloadConverter.to_db_dict(workload_data)
                
                # S'assurer que nous avons un ID
                workload_id = db_workload.get('id')
                if not workload_id:
                    continue
                
                # Insérer ou mettre à jour le workload
                query, params = EntityConverter.prepare_for_insert("workloads", db_workload)
                cursor.execute(query, params)
                stored_count += 1
                
                # Extraire et stocker les labels
                workload_labels = WorkloadConverter.extract_workload_labels(workload_data)
                for label_relation in workload_labels:
                    cursor.execute('''
                    INSERT INTO workload_labels (workload_id, label_id)
                    VALUES (?, ?)
                    ''', (label_relation['workload_id'], label_relation['label_id']))
                
                # Extraire et stocker les interfaces
                interfaces = WorkloadConverter.extract_interfaces(workload_data)
                for interface in interfaces:
                    query, params = EntityConverter.prepare_for_insert("workload_interfaces", interface)
                    cursor.execute(query, params)
        
        return ApiResponse.success(
            data={"stored_count": stored_count},
            message=f"{stored_count} workloads stockés avec succès"
        )
    
    @handle_exceptions
    def get(self, workload_id: str) -> ApiResponse:
        """
        Récupère un workload par son ID.
        
        Args:
            workload_id (str): ID du workload à récupérer
            
        Returns:
            ApiResponse: Réponse contenant le workload ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Récupérer le workload
            cursor.execute('''
            SELECT * FROM workloads WHERE id = ?
            ''', (workload_id,))
            
            row = cursor.fetchone()
            if not row:
                return ApiResponse.error(
                    message=f"Workload avec ID {workload_id} non trouvé",
                    code=404
                )
            
            # Convertir l'enregistrement en dictionnaire
            workload = WorkloadConverter.from_db_row(row)
            
            # Récupérer les labels associés
            cursor.execute('''
            SELECT l.* FROM labels l
            JOIN workload_labels wl ON l.id = wl.label_id
            WHERE wl.workload_id = ?
            ''', (workload_id,))
            
            labels = [dict(label_row) for label_row in cursor.fetchall()]
            workload['labels'] = labels
            
            # Récupérer les interfaces
            cursor.execute('''
            SELECT * FROM workload_interfaces WHERE workload_id = ?
            ''', (workload_id,))
            
            interfaces = []
            for iface_row in cursor.fetchall():
                interface = dict(iface_row)
                
                # Convertir les adresses JSON en liste
                if 'addresses' in interface and interface['addresses']:
                    try:
                        import json
                        interface['addresses'] = json.loads(interface['addresses'])
                    except json.JSONDecodeError:
                        interface['addresses'] = []
                
                interfaces.append(interface)
            
            workload['interfaces'] = interfaces
            
            # Convertir en modèle Workload
            workload_model = self.to_model(workload)
            
            return ApiResponse.success(
                data={
                    "workload": workload,
                    "model": workload_model
                }
            )
    
    @handle_exceptions
    def get_all(self) -> ApiResponse:
        """
        Récupère tous les workloads.
        
        Returns:
            ApiResponse: Réponse contenant la liste des workloads ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM workloads
            ''')
            
            workloads = []
            for row in cursor.fetchall():
                # Convertir l'enregistrement en dictionnaire
                workload = WorkloadConverter.from_db_row(row)
                workloads.append(workload)
            
            # Convertir en modèles
            workload_models = [self.to_model(w) for w in workloads]
            
            return ApiResponse.success(
                data={
                    "workloads": workloads,
                    "models": workload_models,
                    "count": len(workloads)
                }
            )
    
    @handle_exceptions
    def get_by_hostname(self, hostname: str) -> ApiResponse:
        """
        Récupère les workloads par hostname.
        
        Args:
            hostname (str): Nom d'hôte à rechercher (peut contenir des wildcards %)
            
        Returns:
            ApiResponse: Réponse contenant la liste des workloads ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM workloads WHERE hostname LIKE ?
            ''', (hostname,))
            
            workloads = []
            for row in cursor.fetchall():
                # Convertir l'enregistrement en dictionnaire
                workload = WorkloadConverter.from_db_row(row)
                workloads.append(workload)
            
            # Convertir en modèles
            workload_models = [self.to_model(w) for w in workloads]
            
            return ApiResponse.success(
                data={
                    "workloads": workloads,
                    "models": workload_models,
                    "count": len(workloads)
                },
                message=f"{len(workloads)} workloads trouvés pour '{hostname}'"
            )
    
    @handle_exceptions
    def get_by_ip(self, ip_address: str) -> ApiResponse:
        """
        Récupère les workloads par adresse IP.
        
        Args:
            ip_address (str): Adresse IP à rechercher
            
        Returns:
            ApiResponse: Réponse contenant la liste des workloads ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Rechercher dans les champs IP principaux
            cursor.execute('''
            SELECT * FROM workloads WHERE public_ip = ?
            ''', (ip_address,))
            
            workloads = []
            for row in cursor.fetchall():
                # Convertir l'enregistrement en dictionnaire
                workload = WorkloadConverter.from_db_row(row)
                workloads.append(workload)
            
            # Rechercher dans les interfaces
            cursor.execute('''
            SELECT w.* FROM workloads w
            JOIN workload_interfaces i ON w.id = i.workload_id
            WHERE i.address = ? OR i.addresses LIKE ?
            ''', (ip_address, f'%"{ip_address}"%'))
            
            for row in cursor.fetchall():
                # Vérifier si ce workload n'est pas déjà dans la liste
                workload_id = row['id']
                if not any(w.get('id') == workload_id for w in workloads):
                    # Convertir l'enregistrement en dictionnaire
                    workload = WorkloadConverter.from_db_row(row)
                    workloads.append(workload)
            
            # Convertir en modèles
            workload_models = [self.to_model(w) for w in workloads]
            
            return ApiResponse.success(
                data={
                    "workloads": workloads,
                    "models": workload_models,
                    "count": len(workloads)
                },
                message=f"{len(workloads)} workloads trouvés pour l'IP '{ip_address}'"
            )
    
    @handle_exceptions
    def get_by_label(self, key: str, value: Optional[str] = None) -> ApiResponse:
        """
        Récupère les workloads par label.
        
        Args:
            key (str): Clé du label
            value (str, optional): Valeur du label (si None, recherche seulement par clé)
            
        Returns:
            ApiResponse: Réponse contenant la liste des workloads ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            if value:
                # Recherche par clé et valeur
                cursor.execute('''
                SELECT w.* FROM workloads w
                JOIN workload_labels wl ON w.id = wl.workload_id
                JOIN labels l ON wl.label_id = l.id
                WHERE l.key = ? AND l.value = ?
                ''', (key, value))
            else:
                # Recherche par clé uniquement
                cursor.execute('''
                SELECT w.* FROM workloads w
                JOIN workload_labels wl ON w.id = wl.workload_id
                JOIN labels l ON wl.label_id = l.id
                WHERE l.key = ?
                ''', (key,))
            
            workloads = []
            for row in cursor.fetchall():
                # Convertir l'enregistrement en dictionnaire
                workload = WorkloadConverter.from_db_row(row)
                workloads.append(workload)
            
            # Convertir en modèles
            workload_models = [self.to_model(w) for w in workloads]
            
            return ApiResponse.success(
                data={
                    "workloads": workloads,
                    "models": workload_models,
                    "count": len(workloads)
                },
                message=f"{len(workloads)} workloads trouvés pour le label '{key}{':' + value if value else ''}'"
            )
    
    @handle_exceptions
    def delete(self, workload_id: str) -> ApiResponse:
        """
        Supprime un workload par son ID.
        
        Args:
            workload_id (str): ID du workload à supprimer
            
        Returns:
            ApiResponse: Réponse indiquant le succès ou l'échec
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Supprimer les relations avec les labels
            cursor.execute('''
            DELETE FROM workload_labels WHERE workload_id = ?
            ''', (workload_id,))
            
            # Supprimer les interfaces
            cursor.execute('''
            DELETE FROM workload_interfaces WHERE workload_id = ?
            ''', (workload_id,))
            
            # Supprimer le workload
            cursor.execute('''
            DELETE FROM workloads WHERE id = ?
            ''', (workload_id,))
            
            if cursor.rowcount > 0:
                return ApiResponse.success(
                    message=f"Workload {workload_id} supprimé avec succès"
                )
            else:
                return ApiResponse.error(
                    message=f"Workload {workload_id} non trouvé",
                    code=404
                )
    
    def to_model(self, workload_data: Dict[str, Any]) -> Workload:
        """
        Convertit un dictionnaire de workload en modèle.
        
        Args:
            workload_data (dict): Données du workload
            
        Returns:
            Workload: Instance du modèle Workload
        """
        # Utiliser la méthode from_dict du modèle pour créer une instance
        return Workload.from_dict(workload_data)
    
    def from_model(self, workload: Workload) -> Dict[str, Any]:
        """
        Convertit un modèle Workload en dictionnaire.
        
        Args:
            workload (Workload): Instance du modèle Workload
            
        Returns:
            dict: Dictionnaire représentant le workload
        """
        # Utiliser la méthode to_dict du modèle pour obtenir le dictionnaire
        return workload.to_dict()