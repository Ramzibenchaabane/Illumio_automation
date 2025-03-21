# illumio/database/entity_managers/ruleset_manager.py
"""
Gestionnaire des rule sets dans la base de données.
"""
import sqlite3
import json
from ...db_utils import db_connection

class RuleSetManager:
    """Gère les opérations de base de données pour les rule sets et règles."""
    
    def __init__(self, db_file):
        """Initialise le gestionnaire de rule sets.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self):
        """Initialise les tables nécessaires pour les rule sets et règles.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table Rule Sets
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS rule_sets (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    enabled INTEGER,
                    pversion TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Table Rules
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    rule_set_id TEXT,
                    description TEXT,
                    enabled INTEGER,
                    providers TEXT,
                    consumers TEXT,
                    ingress_services TEXT,
                    resolve_labels_as TEXT,
                    sec_connect INTEGER,
                    unscoped_consumers INTEGER,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_set_id) REFERENCES rule_sets (id)
                )
                ''')
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables rule sets: {e}")
            return False
    
    def store_rule_sets(self, rule_sets, pversion='draft'):
        """Stocke les rule sets et leurs règles dans la base de données.
        
        Args:
            rule_sets (list): Liste des rule sets à stocker
            pversion (str): Version de la politique ('draft' ou 'active')
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                for rule_set in rule_sets:
                    # Extraire l'ID depuis l'URL href
                    rule_set_id = rule_set.get('href', '').split('/')[-1] if rule_set.get('href') else None
                    
                    if not rule_set_id:
                        continue
                    
                    # Insérer ou mettre à jour le rule set
                    cursor.execute('''
                    INSERT OR REPLACE INTO rule_sets (id, name, description, enabled, pversion, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        rule_set_id,
                        rule_set.get('name'),
                        rule_set.get('description'),
                        1 if rule_set.get('enabled') else 0,
                        pversion,
                        json.dumps(rule_set)
                    ))
                    
                    # Traiter les règles de ce rule set
                    rules = rule_set.get('rules', [])
                    for rule in rules:
                        rule_id = rule.get('href', '').split('/')[-1] if rule.get('href') else None
                        
                        if not rule_id:
                            continue
                            
                        # Convertir les listes de providers, consumers et services en JSON
                        providers_json = json.dumps(rule.get('providers', []))
                        consumers_json = json.dumps(rule.get('consumers', []))
                        ingress_services_json = json.dumps(rule.get('ingress_services', []))
                        
                        cursor.execute('''
                        INSERT OR REPLACE INTO rules (
                            id, rule_set_id, description, enabled, 
                            providers, consumers, ingress_services, 
                            resolve_labels_as, sec_connect, unscoped_consumers, 
                            raw_data
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            rule_id,
                            rule_set_id,
                            rule.get('description'),
                            1 if rule.get('enabled') else 0,
                            providers_json,
                            consumers_json,
                            ingress_services_json,
                            # Convertir resolve_labels_as en chaîne JSON s'il s'agit d'un dictionnaire
                            json.dumps(rule.get('resolve_labels_as')) if isinstance(rule.get('resolve_labels_as'), dict) else rule.get('resolve_labels_as'),
                            1 if rule.get('sec_connect') else 0,
                            1 if rule.get('unscoped_consumers') else 0,
                            json.dumps(rule)
                        ))
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des rule sets: {e}")
            return False
    
    def get_rule_by_href(self, rule_href):
        """Récupère une règle par son href complet.
        
        Args:
            rule_href (str): Href complet de la règle
            
        Returns:
            dict: Données de la règle ou None si non trouvée
        """
        try:
            # Extraire l'ID de la règle depuis l'URL href
            rule_id = rule_href.split('/')[-1] if rule_href else None
            
            if not rule_id:
                return None
            
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM rules WHERE id = ?
                ''', (rule_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                rule = dict(row)
                
                # Convertir les données JSON en dictionnaires
                if rule.get('raw_data'):
                    rule['raw_data'] = json.loads(rule['raw_data'])
                if rule.get('providers'):
                    rule['providers'] = json.loads(rule['providers'])
                if rule.get('consumers'):
                    rule['consumers'] = json.loads(rule['consumers'])
                if rule.get('ingress_services'):
                    rule['ingress_services'] = json.loads(rule['ingress_services'])
                
                return rule
        
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération de la règle: {e}")
            return None
    
    def get_rules_by_hrefs(self, rule_hrefs):
        """Récupère plusieurs règles par leurs hrefs.
        
        Args:
            rule_hrefs (list): Liste des hrefs des règles
            
        Returns:
            list: Liste des règles correspondantes
        """
        if not rule_hrefs:
            return []
            
        # Extraire les IDs des règles depuis les URLs hrefs
        rule_ids = [href.split('/')[-1] for href in rule_hrefs if href]
        
        if not rule_ids:
            return []
        
        try:
            with db_connection(self.db_file) as (conn, cursor):
                placeholders = ', '.join(['?'] * len(rule_ids))
                query = f'''
                SELECT * FROM rules WHERE id IN ({placeholders})
                '''
                
                cursor.execute(query, rule_ids)
                
                rules = []
                for row in cursor.fetchall():
                    rule = dict(row)
                    
                    # Convertir les données JSON en dictionnaires
                    if rule.get('raw_data'):
                        rule['raw_data'] = json.loads(rule['raw_data'])
                    if rule.get('providers'):
                        rule['providers'] = json.loads(rule['providers'])
                    if rule.get('consumers'):
                        rule['consumers'] = json.loads(rule['consumers'])
                    if rule.get('ingress_services'):
                        rule['ingress_services'] = json.loads(rule['ingress_services'])
                    
                    rules.append(rule)
                
                return rules
        
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des règles: {e}")
            return []
            
    def get_rule_set_by_id(self, rule_set_id):
        """Récupère un rule set par son ID.
        
        Args:
            rule_set_id (str): ID du rule set
            
        Returns:
            dict: Données du rule set ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM rule_sets WHERE id = ?
                ''', (rule_set_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                rule_set = dict(row)
                
                # Convertir les données JSON en dictionnaires
                if rule_set.get('raw_data'):
                    rule_set['raw_data'] = json.loads(rule_set['raw_data'])
                
                # Récupérer les règles de ce rule set
                cursor.execute('''
                SELECT * FROM rules WHERE rule_set_id = ?
                ''', (rule_set_id,))
                
                rules = []
                for rule_row in cursor.fetchall():
                    rule = dict(rule_row)
                    
                    # Convertir les données JSON en dictionnaires
                    if rule.get('raw_data'):
                        rule['raw_data'] = json.loads(rule['raw_data'])
                    if rule.get('providers'):
                        rule['providers'] = json.loads(rule['providers'])
                    if rule.get('consumers'):
                        rule['consumers'] = json.loads(rule['consumers'])
                    if rule.get('ingress_services'):
                        rule['ingress_services'] = json.loads(rule['ingress_services'])
                    
                    rules.append(rule)
                
                rule_set['rules'] = rules
                
                return rule_set
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du rule set: {e}")
            return None