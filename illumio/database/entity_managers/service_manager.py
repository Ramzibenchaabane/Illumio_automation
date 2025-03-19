# illumio/database/entity_manager/service_manager.py
"""
Gestionnaire des services dans la base de données.
"""
import sqlite3
import json
from ...db_utils import db_connection

class ServiceManager:
    """Gère les opérations de base de données pour les services."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire de services.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
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
    
    def store(self, services):
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
                    service_id = service.get('href', '').split('/')[-1] if service.get('href') else None
                    
                    if not service_id:
                        continue
                    
                    # Insérer ou mettre à jour le service
                    cursor.execute('''
                    INSERT OR REPLACE INTO services (id, name, description, raw_data)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        service_id,
                        service.get('name'),
                        service.get('description'),
                        json.dumps(service)
                    ))
                    
                    # Insérer les ports de service
                    for service_port in service.get('service_ports', []):
                        cursor.execute('''
                        INSERT INTO service_ports (service_id, port, to_port, protocol)
                        VALUES (?, ?, ?, ?)
                        ''', (
                            service_id,
                            service_port.get('port'),
                            service_port.get('to_port', service_port.get('port')),  # Si to_port n'est pas défini, utiliser port
                            service_port.get('proto')
                        ))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des services: {e}")
            return False
    
    def get(self, service_id):
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
                
                service = dict(service_row)
                
                # Récupérer les ports du service
                cursor.execute('''
                SELECT * FROM service_ports WHERE service_id = ?
                ''', (service_id,))
                
                service['service_ports'] = [dict(row) for row in cursor.fetchall()]
                
                return service
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du service: {e}")
            return None
    
    def get_all(self):
        """Récupère tous les services.
        
        Returns:
            list: Liste des services
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM services
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des services: {e}")
            return []
    
    def find_by_port_protocol(self, port, protocol):
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
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la recherche des services: {e}")
            return []