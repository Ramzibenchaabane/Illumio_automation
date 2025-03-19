"""
Gestionnaire des listes d'IPs dans la base de données.
"""
import sqlite3
import json
from ...db_utils import db_connection

class IPListManager:
    """Gère les opérations de base de données pour les listes d'IPs."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire de listes d'IPs.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les listes d'IPs.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table IP Lists
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_lists (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Table IP Ranges (liée à IP Lists)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_ranges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_list_id TEXT,
                    from_ip TEXT,
                    to_ip TEXT,
                    description TEXT,
                    exclusion INTEGER,
                    FOREIGN KEY (ip_list_id) REFERENCES ip_lists (id)
                )
                ''')
                
                # Table FQDN (liée à IP Lists)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS fqdns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_list_id TEXT,
                    fqdn TEXT,
                    description TEXT,
                    FOREIGN KEY (ip_list_id) REFERENCES ip_lists (id)
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables des listes d'IPs: {e}")
            return False
    
    def store(self, ip_lists):
        """Stocke les listes d'IPs dans la base de données.
        
        Args:
            ip_lists (list): Liste des listes d'IPs à stocker
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Vider les tables liées pour mise à jour
                cursor.execute("DELETE FROM ip_ranges")
                cursor.execute("DELETE FROM fqdns")
                
                for ip_list in ip_lists:
                    # Extraire l'ID depuis l'URL href
                    ip_list_id = ip_list.get('href', '').split('/')[-1] if ip_list.get('href') else None
                    
                    if not ip_list_id:
                        continue
                    
                    # Insérer ou mettre à jour la liste d'IPs
                    cursor.execute('''
                    INSERT OR REPLACE INTO ip_lists (id, name, description, raw_data)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        ip_list_id,
                        ip_list.get('name'),
                        ip_list.get('description'),
                        json.dumps(ip_list)
                    ))
                    
                    # Insérer les plages d'IPs
                    for ip_range in ip_list.get('ip_ranges', []):
                        cursor.execute('''
                        INSERT INTO ip_ranges (ip_list_id, from_ip, to_ip, description, exclusion)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (
                            ip_list_id,
                            ip_range.get('from_ip'),
                            ip_range.get('to_ip', ip_range.get('from_ip')),  # Si to_ip n'est pas défini, utiliser from_ip
                            ip_range.get('description', ''),
                            1 if ip_range.get('exclusion') else 0
                        ))
                    
                    # Insérer les FQDNs
                    for fqdn_entry in ip_list.get('fqdns', []):
                        cursor.execute('''
                        INSERT INTO fqdns (ip_list_id, fqdn, description)
                        VALUES (?, ?, ?)
                        ''', (
                            ip_list_id,
                            fqdn_entry.get('fqdn'),
                            fqdn_entry.get('description', '')
                        ))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des listes d'IPs: {e}")
            return False
    
    def get(self, ip_list_id):
        """Récupère une liste d'IPs par son ID avec ses plages et FQDNs.
        
        Args:
            ip_list_id (str): ID de la liste d'IPs à récupérer
            
        Returns:
            dict: Données de la liste d'IPs ou None si non trouvée
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Récupérer la liste d'IPs
                cursor.execute('''
                SELECT * FROM ip_lists WHERE id = ?
                ''', (ip_list_id,))
                
                ip_list_row = cursor.fetchone()
                if not ip_list_row:
                    return None
                
                ip_list = dict(ip_list_row)
                
                # Récupérer les plages d'IPs
                cursor.execute('''
                SELECT * FROM ip_ranges WHERE ip_list_id = ?
                ''', (ip_list_id,))
                
                ip_list['ip_ranges'] = [dict(row) for row in cursor.fetchall()]
                
                # Récupérer les FQDNs
                cursor.execute('''
                SELECT * FROM fqdns WHERE ip_list_id = ?
                ''', (ip_list_id,))
                
                ip_list['fqdns'] = [dict(row) for row in cursor.fetchall()]
                
                return ip_list
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération de la liste d'IPs: {e}")
            return None
    
    def get_all(self):
        """Récupère toutes les listes d'IPs.
        
        Returns:
            list: Liste des listes d'IPs
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM ip_lists
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des listes d'IPs: {e}")
            return []