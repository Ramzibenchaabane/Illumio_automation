#illumio/converters/rule_converter.py
"""
Convertisseur pour les règles de sécurité Illumio.

Ce module contient des méthodes spécialisées pour convertir les règles de sécurité
entre leur représentation en base de données et leur représentation en objet.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .entity_converter import EntityConverter


class RuleConverter:
    """Classe pour la conversion des règles de sécurité."""
    
    @staticmethod
    def to_db_dict(rule: Dict[str, Any], rule_set_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Convertit une règle pour stockage en base de données.
        
        Args:
            rule: Règle à convertir
            rule_set_id: ID du rule set parent (optionnel)
            
        Returns:
            Dictionnaire prêt pour insertion en base de données
        """
        if not rule:
            return {}
        
        # Extraire l'ID de la règle
        rule_id = rule.get('id')
        if not rule_id and 'href' in rule:
            # Extraire l'ID depuis l'URL
            href = rule['href']
            rule_id = href.split('/')[-1] if href else None
        
        # Extraire le nom de la règle
        name = rule.get('name', '')
        
        # S'assurer que raw_data contient les scopes si présents
        raw_data = rule.copy() if isinstance(rule, dict) else rule
            
        # Créer une base pour l'entité de base de données
        db_rule = {
            'id': rule_id,
            'name': name,
            'description': rule.get('description'),
            'enabled': 1 if rule.get('enabled') else 0,
            'resolve_labels_as': json.dumps(rule['resolve_labels_as']) if isinstance(rule.get('resolve_labels_as'), dict) else rule.get('resolve_labels_as'),
            'sec_connect': 1 if rule.get('sec_connect') else 0,
            'unscoped_consumers': 1 if rule.get('unscoped_consumers') else 0,
            'raw_data': json.dumps(raw_data) if isinstance(raw_data, dict) else raw_data
        }
        
        # Ajouter l'ID du rule set si fourni
        if rule_set_id:
            db_rule['rule_set_id'] = rule_set_id
        elif 'rule_set_id' in rule:
            db_rule['rule_set_id'] = rule['rule_set_id']
        
        # Convertir les listes en JSON
        list_fields = ['providers', 'consumers', 'ingress_services']
        for field in list_fields:
            if field in rule:
                db_rule[field] = json.dumps(rule[field])
        
        return db_rule
    
    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un enregistrement de base de données en règle.
        
        Args:
            row: Enregistrement de base de données
            
        Returns:
            Règle reconstruite
        """
        if not row:
            return {}
        
        # Convertir d'abord avec le convertisseur générique
        rule = EntityConverter.from_db_row(row)
        
        # Reconstruire la structure de la règle
        normalized_rule = {
            'id': rule.get('id'),
            'name': rule.get('name'),
            'rule_set_id': rule.get('rule_set_id'),
            'description': rule.get('description'),
            'enabled': bool(rule.get('enabled')),
            'sec_connect': bool(rule.get('sec_connect')),
            'unscoped_consumers': bool(rule.get('unscoped_consumers'))
        }
        
        # Traiter resolve_labels_as qui peut être du JSON
        if 'resolve_labels_as' in rule:
            if isinstance(rule['resolve_labels_as'], str):
                try:
                    normalized_rule['resolve_labels_as'] = json.loads(rule['resolve_labels_as'])
                except json.JSONDecodeError:
                    normalized_rule['resolve_labels_as'] = rule['resolve_labels_as']
            else:
                normalized_rule['resolve_labels_as'] = rule['resolve_labels_as']
        
        # Transformer les champs JSON en listes/dictionnaires
        list_fields = ['providers', 'consumers', 'ingress_services']
        for field in list_fields:
            if field in rule:
                if isinstance(rule[field], str):
                    try:
                        normalized_rule[field] = json.loads(rule[field])
                    except json.JSONDecodeError:
                        normalized_rule[field] = []
                else:
                    normalized_rule[field] = rule[field]
        
        # Extraire les scopes depuis raw_data si présent
        if 'raw_data' in rule:
            raw_data = rule['raw_data']
            if isinstance(raw_data, str):
                try:
                    parsed_data = json.loads(raw_data)
                    if isinstance(parsed_data, dict) and 'scopes' in parsed_data:
                        normalized_rule['scopes'] = parsed_data['scopes']
                except json.JSONDecodeError:
                    pass
            elif isinstance(raw_data, dict) and 'scopes' in raw_data:
                normalized_rule['scopes'] = raw_data['scopes']
        
        # Reconstruire le href si nécessaire
        if 'rule_set_id' in normalized_rule and 'id' in normalized_rule:
            rule_set_id = normalized_rule['rule_set_id']
            rule_id = normalized_rule['id']
            normalized_rule['href'] = f"/api/v2/orgs/1/sec_policy/active/rule_sets/{rule_set_id}/sec_rules/{rule_id}"
        
        return normalized_rule
    
    @staticmethod
    def to_db_rule_set(rule_set: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un rule set pour stockage en base de données.
        
        Args:
            rule_set: Rule set à convertir
            
        Returns:
            Dictionnaire prêt pour insertion en base de données
        """
        if not rule_set:
            return {}
        
        # Extraire l'ID du rule set
        rule_set_id = rule_set.get('id')
        if not rule_set_id and 'href' in rule_set:
            # Extraire l'ID depuis l'URL
            href = rule_set['href']
            rule_set_id = href.split('/')[-1] if href else None
        
        # S'assurer que raw_data contient les scopes si présents
        raw_data = rule_set.copy() if isinstance(rule_set, dict) else rule_set
        
        # Créer une base pour l'entité de base de données
        db_rule_set = {
            'id': rule_set_id,
            'name': rule_set.get('name'),
            'description': rule_set.get('description'),
            'enabled': 1 if rule_set.get('enabled') else 0,
            'pversion': rule_set.get('pversion', 'draft'),
            'raw_data': json.dumps(raw_data) if isinstance(raw_data, dict) else raw_data
        }
        
        return db_rule_set
    
    @staticmethod
    def from_db_rule_set(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un enregistrement de base de données en rule set.
        
        Args:
            row: Enregistrement de base de données
            
        Returns:
            Rule set reconstruit
        """
        if not row:
            return {}
        
        # Convertir d'abord avec le convertisseur générique
        rule_set = EntityConverter.from_db_row(row)
        
        # Reconstruire la structure du rule set
        normalized_rule_set = {
            'id': rule_set.get('id'),
            'name': rule_set.get('name'),
            'description': rule_set.get('description'),
            'enabled': bool(rule_set.get('enabled')),
            'pversion': rule_set.get('pversion', 'draft')
        }
        
        # Extraire les scopes depuis raw_data si présent
        if 'raw_data' in rule_set:
            raw_data = rule_set['raw_data']
            if isinstance(raw_data, str):
                try:
                    parsed_data = json.loads(raw_data)
                    if isinstance(parsed_data, dict) and 'scopes' in parsed_data:
                        normalized_rule_set['scopes'] = parsed_data['scopes']
                except json.JSONDecodeError:
                    pass
            elif isinstance(raw_data, dict) and 'scopes' in raw_data:
                normalized_rule_set['scopes'] = raw_data['scopes']
        
        # Reconstruire le href si nécessaire
        if 'id' in normalized_rule_set and 'pversion' in normalized_rule_set:
            rule_set_id = normalized_rule_set['id']
            pversion = normalized_rule_set['pversion']
            normalized_rule_set['href'] = f"/api/v2/orgs/1/sec_policy/{pversion}/rule_sets/{rule_set_id}"
        
        return normalized_rule_set
    
    @staticmethod
    def extract_rules_from_rule_set(rule_set: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrait les règles d'un rule set.
        
        Args:
            rule_set: Rule set contenant des règles
            
        Returns:
            Liste des règles extraites
        """
        if not rule_set:
            return []
        
        # Extraire l'ID du rule set
        rule_set_id = rule_set.get('id')
        if not rule_set_id and 'href' in rule_set:
            href = rule_set['href']
            rule_set_id = href.split('/')[-1] if href else None
        
        # Récupérer les règles
        rules = []
        raw_rules = rule_set.get('rules', [])
        
        if isinstance(raw_rules, list):
            for rule in raw_rules:
                if isinstance(rule, dict):
                    # Ajouter l'ID du rule set à chaque règle
                    rule_with_parent = rule.copy()
                    rule_with_parent['rule_set_id'] = rule_set_id
                    
                    # Si le rule_set a des scopes, les ajouter également à raw_data
                    if 'scopes' in rule_set:
                        if 'raw_data' not in rule_with_parent:
                            rule_with_parent['raw_data'] = rule.copy()
                        elif isinstance(rule_with_parent['raw_data'], dict):
                            rule_with_parent['raw_data']['scopes'] = rule_set['scopes']
                        # Si raw_data est déjà une chaîne JSON, on la laisse telle quelle
                    
                    rules.append(rule_with_parent)
        
        return rules
    
    @staticmethod
    def from_dict(rule_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une règle à partir d'un dictionnaire, en normalisant la structure.
        
        Args:
            rule_dict: Dictionnaire source
            
        Returns:
            Règle normalisée
        """
        if not rule_dict:
            return {}
        
        # Normaliser les champs de base
        rule = {
            'id': rule_dict.get('id'),
            'name': rule_dict.get('name'),
            'href': rule_dict.get('href'),
            'description': rule_dict.get('description'),
            'enabled': bool(rule_dict.get('enabled', True)),
            'sec_connect': bool(rule_dict.get('sec_connect', False)),
            'unscoped_consumers': bool(rule_dict.get('unscoped_consumers', False)),
            'resolve_labels_as': rule_dict.get('resolve_labels_as'),
            'raw_data': rule_dict
        }
        
        # Extraire ou créer les acteurs (providers, consumers)
        if 'providers' in rule_dict:
            providers = rule_dict['providers']
            if isinstance(providers, list):
                providers_list = []
                for provider in providers:
                    if isinstance(provider, dict):
                        providers_list.append(provider)
                rule['providers'] = providers_list
        
        if 'consumers' in rule_dict:
            consumers = rule_dict['consumers']
            if isinstance(consumers, list):
                consumers_list = []
                for consumer in consumers:
                    if isinstance(consumer, dict):
                        consumers_list.append(consumer)
                rule['consumers'] = consumers_list
        
        # Traiter les services
        if 'ingress_services' in rule_dict:
            services = rule_dict['ingress_services']
            if isinstance(services, list):
                services_list = []
                for service in services:
                    if isinstance(service, dict):
                        services_list.append(service)
                rule['services'] = services_list
        
        # Extraire les scopes si présents
        if 'scopes' in rule_dict:
            # Pas besoin de stocker explicitement les scopes car ils sont dans raw_data
            pass
        
        return rule