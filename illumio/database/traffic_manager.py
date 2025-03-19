# illumio/database/traffic_manager.py
"""
Gestionnaire des analyses de trafic dans la base de données.
"""
import sqlite3
import json
import time
from ..db_utils import db_connection

class TrafficManager:
    """Gère les opérations de base de données pour les analyses de trafic."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire d'analyses de trafic.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les analyses de trafic.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
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
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables d'analyse de trafic: {e}")
            return False
    
    def store_query(self, query_data, query_id, status='created'):
        """Stocke une requête de trafic asynchrone dans la base de données.
        
        Args:
            query_data (dict): Données de la requête
            query_id (str): ID de la requête
            status (str): Statut initial de la requête
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
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
            
            return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage de la requête de trafic: {e}")
            return False
    
    def update_query_id(self, temp_id, new_id):
        """Met à jour l'ID d'une requête de trafic temporaire avec l'ID réel de l'API.
        
        Args:
            temp_id (str): ID temporaire de la requête
            new_id (str): Nouvel ID de la requête
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
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
    
    def update_query_status(self, query_id, status, rules_status=None):
        """Met à jour le statut d'une requête de trafic asynchrone.
        
        Args:
            query_id (str): ID de la requête
            status (str): Nouveau statut
            rules_status (str, optional): Statut des règles
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        max_retries = 3
        retry_delay = 1  # secondes

        for attempt in range(max_retries):
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
                
                return True
                    
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"Avertissement lors de la mise à jour du statut de la requête: {e}")
                    print(f"Tentative {attempt+1}/{max_retries}, nouvelle tentative dans {retry_delay} secondes...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    print(f"Erreur lors de la mise à jour du statut de la requête: {e}")
                    return False
            except sqlite3.Error as e:
                print(f"Erreur lors de la mise à jour du statut de la requête: {e}")
                return False
        
        return False
    
    def update_query_rules_status(self, query_id, rules_status):
        """Met à jour le statut des règles d'une requête de trafic asynchrone.
        
        Args:
            query_id (str): ID de la requête
            rules_status (str): Nouveau statut des règles
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        max_retries = 3
        retry_delay = 1  # secondes

        for attempt in range(max_retries):
            try:
                with db_connection(self.db_file) as (conn, cursor):
                    cursor.execute('''
                    UPDATE traffic_queries
                    SET rules_status = ?,
                        rules_completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE rules_completed_at END
                    WHERE id = ?
                    ''', (rules_status, rules_status, query_id))
                
                return True
                    
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"Avertissement lors de la mise à jour du statut des règles: {e}")
                    print(f"Tentative {attempt+1}/{max_retries}, nouvelle tentative dans {retry_delay} secondes...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    print(f"Erreur lors de la mise à jour du statut des règles: {e}")
                    return False
            except sqlite3.Error as e:
                print(f"Erreur lors de la mise à jour du statut des règles: {e}")
                return False
        
        return False
    
    def store_traffic_flows(self, query_id, flows):
        """Stocke les résultats d'une requête de trafic asynchrone.
        
        Args:
            query_id (str): ID de la requête
            flows (list): Liste des flux de trafic
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        max_retries = 3
        retry_delay = 1  # secondes

        for attempt in range(max_retries):
            try:
                with db_connection(self.db_file) as (conn, cursor):
                    # Définir un timeout plus long pour la base de données
                    conn.execute("PRAGMA busy_timeout = 10000")  # 10 secondes de timeout
                    
                    # Supprimer les flux existants pour cette requête
                    cursor.execute("DELETE FROM traffic_flows WHERE query_id = ?", (query_id,))
                    
                    # Traiter chaque flux
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
                        
                        # Gérer les deux formats de rules (dict avec sec_policy ou liste de règles)
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
                            rule_sec_policy = json.dumps(rule)
                        
                        # Extraire les IDs des workloads s'ils existent
                        src_workload_id = src.get('workload', {}).get('href', '').split('/')[-1] if src.get('workload', {}).get('href') else None
                        dst_workload_id = dst.get('workload', {}).get('href', '').split('/')[-1] if dst.get('workload', {}).get('href') else None
                        
                        try:
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
                        except sqlite3.OperationalError as e:
                            if "database is locked" in str(e):
                                # Attendre et réessayer cette insertion
                                time.sleep(0.5)
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
                            else:
                                raise
                    
                    # Mettre à jour le statut de la requête en dehors de la boucle avec délai pour éviter les verrouillages
                    time.sleep(0.5)
                    try:
                        # Utiliser la méthode déjà renforcée pour update_query_status
                        self.update_query_status(
                            query_id, 
                            'completed', 
                            rules_status='completed' if any(
                                isinstance(flow.get('rules'), dict) and 'sec_policy' in flow.get('rules') or 
                                isinstance(flow.get('rules'), list) and len(flow.get('rules')) > 0 
                                for flow in flows
                            ) else None
                        )
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e):
                            # Si l'erreur persiste, on force un délai plus important
                            time.sleep(2)
                            self.update_query_status(
                                query_id, 
                                'completed', 
                                rules_status='completed' if any(
                                    isinstance(flow.get('rules'), dict) and 'sec_policy' in flow.get('rules') or 
                                    isinstance(flow.get('rules'), list) and len(flow.get('rules')) > 0 
                                    for flow in flows
                                ) else None
                            )
                        else:
                            raise
                
                return True
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"Avertissement lors du stockage des flux de trafic: {e}")
                    print(f"Tentative {attempt+1}/{max_retries}, nouvelle tentative dans {retry_delay} secondes...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    print(f"Erreur lors du stockage des flux de trafic: {e}")
                    return False
            except sqlite3.Error as e:
                print(f"Erreur lors du stockage des flux de trafic: {e}")
                return False
        
        return False
    
    def get_queries(self, status=None):
        """Récupère les requêtes de trafic asynchrones avec filtre optionnel sur le statut.
        
        Args:
            status (str, optional): Filtre sur le statut
            
        Returns:
            list: Liste des requêtes correspondantes
        """
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
    
    def get_flows(self, query_id):
        """Récupère les flux de trafic pour une requête spécifique.
        
        Args:
            query_id (str): ID de la requête
            
        Returns:
            list: Liste des flux correspondants
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM traffic_flows WHERE query_id = ?
                ''', (query_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des flux de trafic: {e}")
            return []
    
    def get_query(self, query_id):
        """Récupère les détails d'une requête de trafic.
        
        Args:
            query_id (str): ID de la requête
            
        Returns:
            dict: Détails de la requête ou None si non trouvée
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM traffic_queries WHERE id = ?
                ''', (query_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                return None
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération de la requête: {e}")
            return None
    
    def get_flow_stats(self, query_id):
        """Récupère des statistiques sur les flux d'une requête.
        
        Args:
            query_id (str): ID de la requête
            
        Returns:
            dict: Statistiques sur les flux
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Nombre total de flux
                cursor.execute('''
                SELECT COUNT(*) as total_flows FROM traffic_flows WHERE query_id = ?
                ''', (query_id,))
                total_flows = cursor.fetchone()['total_flows']
                
                # Répartition par décision de politique
                cursor.execute('''
                SELECT policy_decision, COUNT(*) as count 
                FROM traffic_flows 
                WHERE query_id = ? 
                GROUP BY policy_decision
                ''', (query_id,))
                policy_stats = {row['policy_decision']: row['count'] for row in cursor.fetchall()}
                
                # Nombre de flux avec règles identifiées
                cursor.execute('''
                SELECT COUNT(*) as count_with_rules 
                FROM traffic_flows 
                WHERE query_id = ? AND rule_href IS NOT NULL
                ''', (query_id,))
                flows_with_rules = cursor.fetchone()['count_with_rules']
                
                return {
                    'total_flows': total_flows,
                    'policy_stats': policy_stats,
                    'flows_with_rules': flows_with_rules,
                    'rules_percentage': (flows_with_rules / total_flows) * 100 if total_flows > 0 else 0
                }
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            return {}
    
    def delete_query(self, query_id):
        """Supprime une requête de trafic et ses flux associés.
        
        Args:
            query_id (str): ID de la requête à supprimer
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Supprimer d'abord les flux pour respecter les contraintes de clé étrangère
                cursor.execute('''
                DELETE FROM traffic_flows WHERE query_id = ?
                ''', (query_id,))
                
                # Puis supprimer la requête
                cursor.execute('''
                DELETE FROM traffic_queries WHERE id = ?
                ''', (query_id,))
                
                return True
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la suppression de la requête: {e}")
            return False