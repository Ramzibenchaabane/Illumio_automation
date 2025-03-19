# illumio/database.py
"""
Module de gestion de la base de données SQLite pour l'application Illumio.
"""
import os
import sqlite3
import json
from .db_utils import db_connection, execute_query

class IllumioDatabase:
    """Gère la connexion et les opérations avec la base de données SQLite."""
    
    def __init__(self, db_file='data/illumio.db'):
        """Initialise la connexion à la base de données."""
        self.db_file = db_file
        # S'assurer que le dossier de la base de données existe
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    def connect(self):
        """Établit la connexion à la base de données."""
        conn = sqlite3.connect(self.db_file)
        # Permettre d'accéder aux colonnes par nom
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor
    
    def close(self, conn):
        """Ferme la connexion à la base de données."""
        if conn:
            conn.close()
    
    def init_db(self):
        """Initialise la structure de la base de données."""
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
                
                # Tables pour les requêtes de trafic asynchrones
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS traffic_queries (
                    id TEXT PRIMARY KEY,
                    query_name TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    rules_status TEXT,
                    rules_completed_at TIMESTAMP,
                    raw_query TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS traffic_flows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id TEXT,
                    src_ip TEXT,
                    src_workload_id TEXT,
                    dst_ip TEXT,
                    dst_workload_id TEXT,
                    service TEXT,
                    port INTEGER,
                    protocol INTEGER,
                    policy_decision TEXT,
                    first_detected TIMESTAMP,
                    last_detected TIMESTAMP,
                    num_connections INTEGER,
                    flow_direction TEXT,
                    rule_href TEXT,
                    rule_name TEXT,
                    rule_sec_policy TEXT,
                    raw_data TEXT,
                    FOREIGN KEY (query_id) REFERENCES traffic_queries (id),
                    FOREIGN KEY (src_workload_id) REFERENCES workloads (id),
                    FOREIGN KEY (dst_workload_id) REFERENCES workloads (id)
                )
                ''')

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
            print(f"Erreur lors de l'initialisation de la base de données: {e}")
            return False
    
    def store_workloads(self, workloads):
        """Stocke les workloads dans la base de données."""
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
    
    def store_labels(self, labels):
        """Stocke les labels dans la base de données."""
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
    
    def store_ip_lists(self, ip_lists):
        """Stocke les listes d'IPs dans la base de données."""
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
    
    def store_services(self, services):
        """Stocke les services dans la base de données."""
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
    
    def store_label_groups(self, label_groups):
        """Stocke les groupes de labels dans la base de données."""
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

    # Méthodes pour gérer les opérations asynchrones génériques
    
    def store_async_operation(self, operation_id, operation_type, status, data=None, result_id=None):
        """Stocke une opération asynchrone dans la base de données."""
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
    
    def update_async_operation_status(self, operation_id, status, error_message=None):
        """Met à jour le statut d'une opération asynchrone."""
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
    
    def get_async_operation(self, operation_id):
        """Récupère les détails d'une opération asynchrone."""
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
    
    def get_async_operations_by_type(self, operation_type, status=None):
        """Récupère les opérations asynchrones par type et statut optionnel."""
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
    
    def store_traffic_query(self, query_data, query_id, status='created'):
        """Stocke une requête de trafic asynchrone dans la base de données."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                INSERT OR REPLACE INTO traffic_queries 
                (id, query_name, status, created_at, raw_query)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (
                    query_id,
                    query_data.get('query_name'),
                    status,
                    json.dumps(query_data)
                ))
                
                # Également stocker dans la nouvelle table d'opérations asynchrones
                self.store_async_operation(
                    operation_id=query_id,
                    operation_type='traffic_analysis',
                    status=status,
                    data=query_data
                )
            
            return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage de la requête de trafic: {e}")
            return False
    
    def update_traffic_query_id(self, temp_id, new_id):
        """Met à jour l'ID d'une requête de trafic temporaire avec l'ID réel de l'API."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                UPDATE traffic_queries
                SET id = ?
                WHERE id = ?
                ''', (new_id, temp_id))
            
            return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la mise à jour de l'ID de la requête: {e}")
            return False
    
    def update_traffic_query_status(self, query_id, status, rules_status=None):
        """Met à jour le statut d'une requête de trafic asynchrone."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Mise à jour conditionnelle selon les statuts
                if rules_status:
                    # Si nous avons à la fois le statut de la requête et celui des règles
                    if status == 'completed' and rules_status == 'completed':
                        cursor.execute('''
                        UPDATE traffic_queries
                        SET status = ?, 
                            completed_at = CURRENT_TIMESTAMP,
                            rules_status = ?,
                            rules_completed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        ''', (status, rules_status, query_id))
                    else:
                        cursor.execute('''
                        UPDATE traffic_queries
                        SET status = ?, 
                            completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END,
                            rules_status = ?
                        WHERE id = ?
                        ''', (status, status, rules_status, query_id))
                else:
                    # Mise à jour du statut de la requête uniquement
                    cursor.execute('''
                    UPDATE traffic_queries
                    SET status = ?, 
                        completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
                    WHERE id = ?
                    ''', (status, status, query_id))
                
                # Également mettre à jour dans la nouvelle table d'opérations asynchrones
                self.update_async_operation_status(query_id, status)
            
            return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la mise à jour du statut de la requête: {e}")
            return False
    
    def update_traffic_query_rules_status(self, query_id, rules_status):
        """Met à jour le statut des règles d'une requête de trafic asynchrone."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                UPDATE traffic_queries
                SET rules_status = ?,
                    rules_completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE rules_completed_at END
                WHERE id = ?
                ''', (rules_status, rules_status, query_id))
            
            return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la mise à jour du statut des règles: {e}")
            return False
    
    def store_traffic_flows(self, query_id, flows):
        """Stocke les résultats d'une requête de trafic asynchrone."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Supprimer les flux existants pour cette requête
                cursor.execute("DELETE FROM traffic_flows WHERE query_id = ?", (query_id,))
                
                for flow in flows:
                    # Extraire les informations source et destination
                    src = flow.get('src', {})
                    dst = flow.get('dst', {})
                    service = flow.get('service', {})
                    timestamp_range = flow.get('timestamp_range', {})
                    
                    # Extraire les informations de règles si disponibles
                    rules = flow.get('rules', {})
                    rule_href = None
                    rule_name = None
                    rule_sec_policy = None
                    
                    # CORRECTION: Gérer les deux formats de rules (dict avec sec_policy ou liste de règles)
                    if isinstance(rules, dict) and 'sec_policy' in rules:
                        # Ancien format (avant update_rules)
                        sec_policy = rules.get('sec_policy', {})
                        if sec_policy:
                            rule_href = sec_policy.get('href')
                            rule_name = sec_policy.get('name')
                            rule_sec_policy = json.dumps(sec_policy)
                    elif isinstance(rules, list) and len(rules) > 0:
                        # Nouveau format (après update_rules) - liste d'objets rule
                        rule = rules[0]  # Prendre la première règle
                        rule_href = rule.get('href')
                        # Note: Le nom de la règle n'est pas disponible dans ce format
                        # On pourrait faire une requête supplémentaire à l'API pour l'obtenir
                        rule_sec_policy = json.dumps(rule)
                    
                    # Extraire les IDs des workloads s'ils existent
                    src_workload_id = src.get('workload', {}).get('href', '').split('/')[-1] if src.get('workload', {}).get('href') else None
                    dst_workload_id = dst.get('workload', {}).get('href', '').split('/')[-1] if dst.get('workload', {}).get('href') else None
                    
                    cursor.execute('''
                    INSERT INTO traffic_flows 
                    (query_id, src_ip, src_workload_id, dst_ip, dst_workload_id, 
                    service, port, protocol, policy_decision, first_detected, 
                    last_detected, num_connections, flow_direction, rule_href,
                    rule_name, rule_sec_policy, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        query_id,
                        src.get('ip'),
                        src_workload_id,
                        dst.get('ip'),
                        dst_workload_id,
                        service.get('name'),
                        service.get('port'),
                        service.get('proto'),
                        flow.get('policy_decision'),
                        timestamp_range.get('first_detected'),
                        timestamp_range.get('last_detected'),
                        flow.get('num_connections'),
                        flow.get('flow_direction'),
                        rule_href,
                        rule_name,
                        rule_sec_policy,
                        json.dumps(flow)
                    ))
                
                # Mettre à jour le statut de la requête
                self.update_traffic_query_status(query_id, 'completed', rules_status='completed' if rules else None)
                
                # Mettre à jour les données dans la table d'opérations asynchrones
                cursor.execute('''
                UPDATE async_operations
                SET result_id = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (query_id, query_id))
            
            return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des flux de trafic: {e}")
            return False
    
    def get_traffic_queries(self, status=None):
        """Récupère les requêtes de trafic asynchrones avec filtre optionnel sur le statut."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                if status:
                    cursor.execute('''
                    SELECT * FROM traffic_queries WHERE status = ? ORDER BY created_at DESC
                    ''', (status,))
                else:
                    cursor.execute('''
                    SELECT * FROM traffic_queries ORDER BY created_at DESC
                    ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des requêtes de trafic: {e}")
            return []
    
    def get_traffic_flows(self, query_id):
        """Récupère les flux de trafic pour une requête spécifique."""
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM traffic_flows WHERE query_id = ?
                ''', (query_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des flux de trafic: {e}")
            return []