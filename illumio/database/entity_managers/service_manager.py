# illumio/database/entity_managers/service_manager.py
"""
Gestionnaire des services dans la base de données.
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional, Union, Tuple

from ...db_utils import db_connection
from ...converters.entity_converter import EntityConverter

class ServiceManager:
    """Gère les opérations de base de données pour les services."""
    
    def __init__(self, db_file: str):
        """Initialise le gestionnaire de services.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self) -> bool:
        """Initialise les tables nécessaires pour les services.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table Services
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Table Service Ports (liée à Services)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_ports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id TEXT,
                    port INTEGER,
                    to_port INTEGER,
                    protocol INTEGER,
                    FOREIGN KEY (service_id) REFERENCES services (id)
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables services: {e}")
            return False
    
    def store(self, services: List[Dict[str, Any]]) -> bool:
        """Stocke les services dans la base de données.
        
        Args:
            services (list): Liste des services à stocker
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Vider la table des ports de service pour mise à jour
                cursor.execute("DELETE FROM service_ports")
                
                for service in services:
                    # Extraire l'ID depuis l'URL href
                    service_id = EntityConverter.extract_id_from_href(service.get('href', ''))
                    
                    if not service_id:
                        continue
                    
                    # Préparer les données du service pour la base de données
                    db_service = {
                        'id': service_id,
                        'name': service.get('name'),
                        'description': service.get('description'),
                        'raw_data': json.dumps(service) if isinstance(service, dict) else service
                    }
                    
                    # Insérer ou mettre à jour le service
                    query, params = EntityConverter.prepare_for_insert("services", db_service)
                    cursor.execute(query, params)
                    
                    # Insérer les ports de service
                    service_ports = service.get('service_ports', [])
                    for service_port in service_ports:
                        if not isinstance(service_port, dict):
                            continue
                            
                        # Extraire les données du port
                        port = service_port.get('port')
                        to_port = service_port.get('to_port', port)  # Si to_port n'est pas défini, utiliser port
                        protocol = service_port.get('proto')
                        
                        # Insérer le port
                        cursor.execute('''
                        INSERT INTO service_ports (service_id, port, to_port, protocol)
                        VALUES (?, ?, ?, ?)
                        ''', (service_id, port, to_port, protocol))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des services: {e}")
            return False
    
    def get(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un service par son ID avec ses ports.
        
        Args:
            service_id (str): ID du service à récupérer
            
        Returns:
            dict: Données du service ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Récupérer le service
                cursor.execute('''
                SELECT * FROM services WHERE id = ?
                ''', (service_id,))
                
                service_row = cursor.fetchone()
                if not service_row:
                    return None
                
                # Convertir l'enregistrement en dictionnaire
                service = EntityConverter.from_db_row(service_row)
                
                # Récupérer les ports du service
                cursor.execute('''
                SELECT * FROM service_ports WHERE service_id = ?
                ''', (service_id,))
                
                # Transformer les rangées en liste de dictionnaires
                service_ports = []
                for row in cursor.fetchall():
                    if hasattr(row, 'keys'):
                        service_port = {key: row[key] for key in row.keys()}
                    else:
                        service_port = dict(row)
                    service_ports.append(service_port)
                
                # Ajouter les ports au service
                service['service_ports'] = service_ports
                
                return service
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du service: {e}")
            return None
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Récupère tous les services.
        
        Returns:
            list: Liste des services
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM services
                ''')
                
                services = []
                for row in cursor.fetchall():
                    # Convertir l'enregistrement en dictionnaire
                    service = EntityConverter.from_db_row(row)
                    services.append(service)
                
                # Pour chaque service, récupérer ses ports
                for service in services:
                    service_id = service.get('id')
                    if service_id:
                        cursor.execute('''
                        SELECT * FROM service_ports WHERE service_id = ?
                        ''', (service_id,))
                        
                        # Transformer les rangées en liste de dictionnaires
                        service_ports = []
                        for port_row in cursor.fetchall():
                            if hasattr(port_row, 'keys'):
                                service_port = {key: port_row[key] for key in port_row.keys()}
                            else:
                                service_port = dict(port_row)
                            service_ports.append(service_port)
                        
                        # Ajouter les ports au service
                        service['service_ports'] = service_ports
                
                return services
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des services: {e}")
            return []
    
    def find_by_port_protocol(self, port: int, protocol: int) -> List[Dict[str, Any]]:
        """Trouve les services par port et protocole.
        
        Args:
            port (int): Numéro de port
            protocol (int): Numéro de protocole
            
        Returns:
            list: Liste des services correspondants
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT s.* FROM services s
                JOIN service_ports sp ON s.id = sp.service_id
                WHERE sp.port <= ? AND sp.to_port >= ? AND sp.protocol = ?
                ''', (port, port, protocol))
                
                services = []
                for row in cursor.fetchall():
                    # Convertir l'enregistrement en dictionnaire
                    service = EntityConverter.from_db_row(row)
                    
                    # Récupérer les ports du service
                    service_id = service.get('id')
                    if service_id:
                        cursor.execute('''
                        SELECT * FROM service_ports WHERE service_id = ?
                        ''', (service_id,))
                        
                        # Transformer les rangées en liste de dictionnaires
                        service_ports = []
                        for port_row in cursor.fetchall():
                            if hasattr(port_row, 'keys'):
                                service_port = {key: port_row[key] for key in port_row.keys()}
                            else:
                                service_port = dict(port_row)
                            service_ports.append(service_port)
                        
                        # Ajouter les ports au service
                        service['service_ports'] = service_ports
                    
                    services.append(service)
                
                return services
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la recherche des services: {e}")
            return []
    
    def delete(self, service_id: str) -> bool:
        """Supprime un service et ses ports par son ID.
        
        Args:
            service_id (str): ID du service à supprimer
            
        Returns:
            bool: True si la suppression réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Supprimer les ports du service
                cursor.execute('''
                DELETE FROM service_ports WHERE service_id = ?
                ''', (service_id,))
                
                # Supprimer le service
                cursor.execute('''
                DELETE FROM services WHERE id = ?
                ''', (service_id,))
                
                return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la suppression du service: {e}")
            return False