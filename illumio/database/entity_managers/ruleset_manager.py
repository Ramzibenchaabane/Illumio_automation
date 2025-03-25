# illumio/database/entity_managers/ruleset_manager.py
"""
Gestionnaire des rule sets dans la base de données.
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional, Union

from ...db_utils import db_connection
from ...converters.rule_converter import RuleConverter
from ...converters.entity_converter import EntityConverter
from ...models.rule import Rule, RuleSet

class RuleSetManager:
    """Gère les opérations de base de données pour les rule sets et règles."""
    
    def __init__(self, db_file: str):
        """Initialise le gestionnaire de rule sets.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self) -> bool:
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
                    name TEXT,
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
                
                # Ajouter un index pour les recherches rapides par rule_set_id
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_rules_rule_set_id ON rules(rule_set_id)
                ''')
                
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables rule sets: {e}")
            return False
    
    def store_rule_sets(self, rule_sets: List[Dict[str, Any]], pversion: str = 'draft') -> bool:
        """Stocke les rule sets et leurs règles dans la base de données.
        
        Args:
            rule_sets (list): Liste des rule sets à stocker
            pversion (str): Version de la politique ('draft' ou 'active')
            
        Returns:
            bool: True si l'opération réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Pour chaque rule set
                for rule_set_data in rule_sets:
                    # Convertir le rule set en format DB
                    db_rule_set = RuleConverter.to_db_rule_set(rule_set_data)
                    
                    # S'assurer que raw_data contient toutes les informations, y compris les scopes
                    if isinstance(rule_set_data, dict) and 'raw_data' not in db_rule_set:
                        db_rule_set['raw_data'] = json.dumps(rule_set_data)
                    
                    # Ajouter la version de politique
                    db_rule_set['pversion'] = pversion
                    
                    # Insérer le rule set
                    query, params = EntityConverter.prepare_for_insert("rule_sets", db_rule_set)
                    cursor.execute(query, params)
                    
                    # Extraire l'ID du rule set
                    rule_set_id = db_rule_set.get('id')
                    if not rule_set_id:
                        continue
                    
                    # Extraire les règles du rule set
                    rules = RuleConverter.extract_rules_from_rule_set(rule_set_data)
                    
                    # Stocker chaque règle
                    for rule_data in rules:
                        # S'assurer que raw_data contient toutes les informations
                        if 'raw_data' not in rule_data and isinstance(rule_data, dict):
                            rule_data['raw_data'] = json.dumps(rule_data)
                            
                        # Convertir la règle en format DB
                        db_rule = RuleConverter.to_db_dict(rule_data, rule_set_id)
                        
                        # Insérer la règle
                        query, params = EntityConverter.prepare_for_insert("rules", db_rule)
                        cursor.execute(query, params)
            
            return True
        
        except sqlite3.Error as e:
            print(f"Erreur lors du stockage des rule sets: {e}")
            return False
    
    def get_rule_by_href(self, rule_href: str) -> Optional[Dict[str, Any]]:
        """Récupère une règle par son href complet.
        
        Args:
            rule_href (str): Href complet de la règle
            
        Returns:
            dict: Données de la règle ou None si non trouvée
        """
        try:
            # Extraire l'ID de la règle depuis l'URL href
            rule_id = EntityConverter.extract_id_from_href(rule_href)
            
            if not rule_id:
                return None
            
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM rules WHERE id = ?
                ''', (rule_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convertir l'enregistrement en dictionnaire
                rule = RuleConverter.from_db_row(dict(row))
                return rule
        
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération de la règle: {e}")
            return None
    
    def get_rules_by_hrefs(self, rule_hrefs: List[str]) -> List[Dict[str, Any]]:
        """Récupère plusieurs règles par leurs hrefs.
        
        Args:
            rule_hrefs (list): Liste des hrefs des règles
            
        Returns:
            list: Liste des règles correspondantes
        """
        if not rule_hrefs:
            return []
            
        # Extraire les IDs des règles depuis les URLs hrefs
        rule_ids = [EntityConverter.extract_id_from_href(href) for href in rule_hrefs if href]
        rule_ids = [rule_id for rule_id in rule_ids if rule_id]  # Filtrer les None
        
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
                    # Convertir l'enregistrement en dictionnaire
                    rule = RuleConverter.from_db_row(dict(row))
                    rules.append(rule)
                
                return rules
        
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des règles: {e}")
            return []
            
    def get_rule_set_by_id(self, rule_set_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un rule set par son ID.
        
        Args:
            rule_set_id (str): ID du rule set
            
        Returns:
            dict: Données du rule set ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Récupérer le rule set
                cursor.execute('''
                SELECT * FROM rule_sets WHERE id = ?
                ''', (rule_set_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convertir l'enregistrement en dictionnaire
                rule_set = RuleConverter.from_db_rule_set(dict(row))
                
                # Récupérer les règles de ce rule set
                cursor.execute('''
                SELECT * FROM rules WHERE rule_set_id = ?
                ''', (rule_set_id,))
                
                rules = []
                for rule_row in cursor.fetchall():
                    # Convertir l'enregistrement en dictionnaire
                    rule = RuleConverter.from_db_row(dict(rule_row))
                    rules.append(rule)
                
                # Ajouter les règles au rule set
                rule_set['rules'] = rules
                
                return rule_set
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du rule set: {e}")
            return None
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une règle par son ID.
        
        Args:
            rule_id (str): ID de la règle
            
        Returns:
            dict: Données de la règle ou None si non trouvée
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT * FROM rules WHERE id = ?
                ''', (rule_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convertir l'enregistrement en dictionnaire
                rule = RuleConverter.from_db_row(dict(row))
                return rule
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération de la règle: {e}")
            return None
    
    def get_rule_set_name(self, rule_set_id: str) -> Optional[str]:
        """Récupère le nom d'un rule set par son ID.
        
        Args:
            rule_set_id (str): ID du rule set
            
        Returns:
            str: Nom du rule set ou None si non trouvé
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                cursor.execute('''
                SELECT name FROM rule_sets WHERE id = ?
                ''', (rule_set_id,))
                
                row = cursor.fetchone()
                if row:
                    return row['name']
                
                return None
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération du nom du rule set: {e}")
            return None
    
    def get_all_rule_sets(self, pversion: str = None) -> List[Dict[str, Any]]:
        """Récupère tous les rule sets.
        
        Args:
            pversion (str, optional): Version de la politique pour filtrer
            
        Returns:
            list: Liste des rule sets
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                if pversion:
                    cursor.execute('''
                    SELECT * FROM rule_sets WHERE pversion = ?
                    ''', (pversion,))
                else:
                    cursor.execute('''
                    SELECT * FROM rule_sets
                    ''')
                
                rule_sets = []
                for row in cursor.fetchall():
                    # Convertir l'enregistrement en dictionnaire
                    rule_set = RuleConverter.from_db_rule_set(dict(row))
                    rule_sets.append(rule_set)
                
                return rule_sets
                
        except sqlite3.Error as e:
            print(f"Erreur lors de la récupération des rule sets: {e}")
            return []
    
    def to_model(self, rule_data: Dict[str, Any]) -> Rule:
        """Convertit un dictionnaire de règle en modèle.
        
        Args:
            rule_data (dict): Données de la règle
            
        Returns:
            Rule: Instance du modèle Rule
        """
        return Rule.from_dict(rule_data)
    
    def rule_set_to_model(self, rule_set_data: Dict[str, Any]) -> RuleSet:
        """Convertit un dictionnaire de rule set en modèle.
        
        Args:
            rule_set_data (dict): Données du rule set
            
        Returns:
            RuleSet: Instance du modèle RuleSet
        """
        return RuleSet.from_dict(rule_set_data)