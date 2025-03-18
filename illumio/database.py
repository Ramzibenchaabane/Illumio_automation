import sqlite3
import json
import os

class IllumioDatabase:
    """Gère la connexion et les opérations avec la base de données SQLite."""
    
    def __init__(self, db_file='data/illumio.db'):
        """Initialise la connexion à la base de données."""
        # S'assurer que le dossier de la base de données existe
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        
        self.db_file = db_file
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Établit la connexion à la base de données."""
        self.conn = sqlite3.connect(self.db_file)
        # Permettre d'accéder aux colonnes par nom
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self.conn
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
    
    def init_db(self):
        """Initialise la structure de la base de données."""
        try:
            self.connect()
            
            # Table Workloads
            self.cursor.execute('''
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
            
            # Table Labels
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS labels (
                id TEXT PRIMARY KEY,
                key TEXT,
                value TEXT,
                raw_data TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table IP Lists
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_lists (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                raw_data TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table IP Ranges (liée à IP Lists)
            self.cursor.execute('''
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
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fqdns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_list_id TEXT,
                fqdn TEXT,
                description TEXT,
                FOREIGN KEY (ip_list_id) REFERENCES ip_lists (id)
            )
            ''')
            
            # Table Services
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                raw_data TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table Service Ports (liée à Services)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_ports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id TEXT,
                port INTEGER,
                to_port INTEGER,
                protocol INTEGER,
                FOREIGN KEY (service_id) REFERENCES services (id)
            )
            ''')
            
            # Table Label Groups
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS label_groups (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                raw_data TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Table pour les relations entre Label Groups et Labels
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS label_group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label_group_id TEXT,
                label_id TEXT,
                FOREIGN KEY (label_group_id) REFERENCES label_groups (id),
                FOREIGN KEY (label_id) REFERENCES labels (id)
            )
            ''')
            
            # Table pour les relations entre Workloads et Labels
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS workload_labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workload_id TEXT,
                label_id TEXT,
                FOREIGN KEY (workload_id) REFERENCES workloads (id),
                FOREIGN KEY (label_id) REFERENCES labels (id)
            )
            ''')
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation de la base de données: {e}")
            return False
        
        finally:
            self.close()
    
    def store_workloads(self, workloads):
        """Stocke les workloads dans la base de données."""
        try:
            self.connect()
            
            # Vider la table des workloads-labels pour mise à jour
            self.cursor.execute("DELETE FROM workload_labels")
            
            for workload in workloads:
                # Extraire l'ID depuis l'URL href
                workload_id = workload.get('href', '').split('/')[-1] if workload.get('href') else None
                
                if not workload_id:
                    continue
                
                # Insérer ou mettre à jour le workload
                self.cursor.execute('''
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
                        self.cursor.execute('''
                        INSERT INTO workload_labels (workload_id, label_id)
                        VALUES (?, ?)
                        ''', (workload_id, label_id))
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des workloads: {e}")
            self.conn.rollback()
            return False
        
        finally:
            self.close()
    
    def store_labels(self, labels):
        """Stocke les labels dans la base de données."""
        try:
            self.connect()
            
            for label in labels:
                # Extraire l'ID depuis l'URL href
                label_id = label.get('href', '').split('/')[-1] if label.get('href') else None
                
                if not label_id:
                    continue
                
                # Insérer ou mettre à jour le label
                self.cursor.execute('''
                INSERT OR REPLACE INTO labels (id, key, value, raw_data)
                VALUES (?, ?, ?, ?)
                ''', (
                    label_id,
                    label.get('key'),
                    label.get('value'),
                    json.dumps(label)
                ))
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des labels: {e}")
            self.conn.rollback()
            return False
        
        finally:
            self.close()
    
    def store_ip_lists(self, ip_lists):
        """Stocke les listes d'IPs dans la base de données."""
        try:
            self.connect()
            
            # Vider les tables liées pour mise à jour
            self.cursor.execute("DELETE FROM ip_ranges")
            self.cursor.execute("DELETE FROM fqdns")
            
            for ip_list in ip_lists:
                # Extraire l'ID depuis l'URL href
                ip_list_id = ip_list.get('href', '').split('/')[-1] if ip_list.get('href') else None
                
                if not ip_list_id:
                    continue
                
                # Insérer ou mettre à jour la liste d'IPs
                self.cursor.execute('''
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
                    self.cursor.execute('''
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
                    self.cursor.execute('''
                    INSERT INTO fqdns (ip_list_id, fqdn, description)
                    VALUES (?, ?, ?)
                    ''', (
                        ip_list_id,
                        fqdn_entry.get('fqdn'),
                        fqdn_entry.get('description', '')
                    ))
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des listes d'IPs: {e}")
            self.conn.rollback()
            return False
        
        finally:
            self.close()
    
    def store_services(self, services):
        """Stocke les services dans la base de données."""
        try:
            self.connect()
            
            # Vider la table des ports de service pour mise à jour
            self.cursor.execute("DELETE FROM service_ports")
            
            for service in services:
                # Extraire l'ID depuis l'URL href
                service_id = service.get('href', '').split('/')[-1] if service.get('href') else None
                
                if not service_id:
                    continue
                
                # Insérer ou mettre à jour le service
                self.cursor.execute('''
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
                    self.cursor.execute('''
                    INSERT INTO service_ports (service_id, port, to_port, protocol)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        service_id,
                        service_port.get('port'),
                        service_port.get('to_port', service_port.get('port')),  # Si to_port n'est pas défini, utiliser port
                        service_port.get('proto')
                    ))
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des services: {e}")
            self.conn.rollback()
            return False
        
        finally:
            self.close()
    
    def store_label_groups(self, label_groups):
        """Stocke les groupes de labels dans la base de données."""
        try:
            self.connect()
            
            # Vider la table des membres de groupe pour mise à jour
            self.cursor.execute("DELETE FROM label_group_members")
            
            for label_group in label_groups:
                # Extraire l'ID depuis l'URL href
                label_group_id = label_group.get('href', '').split('/')[-1] if label_group.get('href') else None
                
                if not label_group_id:
                    continue
                
                # Insérer ou mettre à jour le groupe de labels
                self.cursor.execute('''
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
                        self.cursor.execute('''
                        INSERT INTO label_group_members (label_group_id, label_id)
                        VALUES (?, ?)
                        ''', (label_group_id, member_id))
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des groupes de labels: {e}")
            self.conn.rollback()
            return False
        
        finally:
            self.close()