#illumio/parsers/rule_parser.py
"""
Parseur spécialisé pour les règles de sécurité Illumio.

Ce module contient des méthodes pour transformer les données brutes des règles
de sécurité provenant de l'API Illumio PCE en structures normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union, Set

from .api_response_parser import ApiResponseParser


class RuleParser:
    """Classe pour parser les règles de sécurité Illumio."""
    
    @staticmethod
    def parse_rule_reference(rules_data: Any) -> Dict[str, Optional[str]]:
        """
        Parse la référence à une règle depuis différents formats de données.
        
        Args:
            rules_data: Données de règle au format dict ou list
            
        Returns:
            dict: Dictionnaire contenant href et name de la règle
        """
        if rules_data is None:
            return {'href': None, 'name': None}
            
        # Format 1: {"sec_policy": {"href": "...", "name": "..."}}
        if isinstance(rules_data, dict) and 'sec_policy' in rules_data:
            sec_policy = rules_data.get('sec_policy', {})
            if isinstance(sec_policy, dict):
                return {
                    'href': sec_policy.get('href'),
                    'name': sec_policy.get('name')
                }
            elif isinstance(sec_policy, str):
                # Parfois sec_policy peut être juste l'URL
                return {
                    'href': sec_policy,
                    'name': ApiResponseParser.extract_id_from_href(sec_policy)
                }
        
        # Format 2: [{"href": "...", "name": "..."}, ...]
        elif isinstance(rules_data, list) and rules_data:
            first_rule = rules_data[0]
            if isinstance(first_rule, dict):
                href = first_rule.get('href')
                name = first_rule.get('name')
                if name is None and href:
                    name = ApiResponseParser.extract_id_from_href(href)
                return {
                    'href': href,
                    'name': name
                }
        
        # Format inconnu, retourner des valeurs vides
        return {'href': None, 'name': None}
    
    @staticmethod
    def parse_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse une règle complète.
        
        Args:
            rule_data: Données brutes de la règle
            
        Returns:
            Dictionnaire normalisé de la règle
        """
        # Si rule_data est un objet ou contient des données JSON brutes
        if not isinstance(rule_data, dict):
            if hasattr(rule_data, '__dict__'):
                rule_data = rule_data.__dict__
            else:
                return {
                    'error': f"Type de règle non supporté: {type(rule_data)}",
                    'raw_data': str(rule_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        raw_data = rule_data.get('raw_data')
        if isinstance(raw_data, str):
            parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
            if parsed_raw_data:
                # Extraire les données de raw_data
                raw_data = parsed_raw_data
        elif isinstance(raw_data, dict):
            # raw_data est déjà un dictionnaire
            pass
        else:
            # Utiliser rule_data directement si raw_data n'est pas utilisable
            raw_data = rule_data
        
        # Extraction de l'ID de la règle
        rule_id = rule_data.get('id') or rule_data.get('rule_id')
        if not rule_id and isinstance(raw_data, dict):
            # Essayer d'extraire de raw_data
            rule_id = raw_data.get('id')
            if not rule_id and 'href' in raw_data:
                rule_id = ApiResponseParser.extract_id_from_href(raw_data['href'])
        
        # Extraction du href
        href = rule_data.get('href')
        if not href and isinstance(raw_data, dict):
            href = raw_data.get('href')
        
        # Construction de la règle normalisée
        normalized_rule = {
            'id': rule_id,
            'href': href,
            'description': RuleParser._extract_description(rule_data, raw_data),
            'enabled': RuleParser._extract_enabled(rule_data, raw_data),
            'providers': RuleParser._parse_actors(rule_data.get('providers') or raw_data.get('providers', [])),
            'consumers': RuleParser._parse_actors(rule_data.get('consumers') or raw_data.get('consumers', [])),
            'services': RuleParser._parse_services(rule_data.get('ingress_services') or raw_data.get('ingress_services', [])),
            'resolve_labels_as': rule_data.get('resolve_labels_as') or raw_data.get('resolve_labels_as'),
            'sec_connect': rule_data.get('sec_connect') or raw_data.get('sec_connect', False),
            'unscoped_consumers': rule_data.get('unscoped_consumers') or raw_data.get('unscoped_consumers', False)
        }
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_rule:
            normalized_rule['raw_data'] = json.dumps(raw_data) if isinstance(raw_data, dict) else str(raw_data)
        
        return normalized_rule
    
    @staticmethod
    def _extract_description(rule_data: Dict[str, Any], raw_data: Dict[str, Any]) -> Optional[str]:
        """Extrait la description d'une règle."""
        description = rule_data.get('description')
        if description:
            return description
        
        if isinstance(raw_data, dict):
            return raw_data.get('description')
        
        return None
    
    @staticmethod
    def _extract_enabled(rule_data: Dict[str, Any], raw_data: Dict[str, Any]) -> bool:
        """Extrait l'état d'activation d'une règle."""
        enabled = rule_data.get('enabled')
        if enabled is not None:
            return bool(enabled)
        
        if isinstance(raw_data, dict):
            return bool(raw_data.get('enabled', False))
        
        return False
    
    @staticmethod
    def _parse_actors(actors_data: Any) -> List[Dict[str, Any]]:
        """
        Parse les acteurs (providers ou consumers) d'une règle.
        
        Args:
            actors_data: Données brutes des acteurs
            
        Returns:
            Liste des acteurs normalisés
        """
        if not actors_data:
            return []
        
        # Si c'est une chaîne JSON, la convertir
        if isinstance(actors_data, str):
            try:
                actors_data = json.loads(actors_data)
            except json.JSONDecodeError:
                return []
        
        if not isinstance(actors_data, list):
            return []
        
        normalized_actors = []
        for actor in actors_data:
            if not isinstance(actor, dict):
                continue
                
            actor_type = None
            actor_value = None
            
            # Détecter le type d'acteur
            if 'actors' in actor and actor['actors'] == 'ams':
                actor_type = 'ams'
                actor_value = 'All Managed Systems'
            elif 'label' in actor and isinstance(actor['label'], dict):
                actor_type = 'label'
                label = actor['label']
                key = label.get('key')
                value = label.get('value')
                if key and value:
                    actor_value = f"{key}:{value}"
                else:
                    actor_value = key or "unknown_label"
            elif 'label_group' in actor and isinstance(actor['label_group'], dict):
                actor_type = 'label_group'
                lg = actor['label_group']
                actor_value = lg.get('name') or ApiResponseParser.extract_id_from_href(lg.get('href'))
            elif 'workload' in actor and isinstance(actor['workload'], dict):
                actor_type = 'workload'
                wl = actor['workload']
                actor_value = wl.get('name') or ApiResponseParser.extract_id_from_href(wl.get('href'))
            elif 'ip_list' in actor and isinstance(actor['ip_list'], dict):
                actor_type = 'ip_list'
                ip = actor['ip_list']
                actor_value = ip.get('name') or ApiResponseParser.extract_id_from_href(ip.get('href'))
            
            if actor_type and actor_value:
                normalized_actors.append({
                    'type': actor_type,
                    'value': actor_value,
                    'raw_data': actor
                })
        
        return normalized_actors
    
    @staticmethod
    def _parse_services(services_data: Any) -> List[Dict[str, Any]]:
        """
        Parse les services d'une règle.
        
        Args:
            services_data: Données brutes des services
            
        Returns:
            Liste des services normalisés
        """
        if not services_data:
            return []
        
        # Si c'est une chaîne JSON, la convertir
        if isinstance(services_data, str):
            try:
                services_data = json.loads(services_data)
            except json.JSONDecodeError:
                return []
        
        if not isinstance(services_data, list):
            return []
        
        normalized_services = []
        for service in services_data:
            if not isinstance(service, dict):
                continue
                
            if 'href' in service:
                # Service référencé
                service_id = ApiResponseParser.extract_id_from_href(service['href'])
                normalized_services.append({
                    'type': 'service',
                    'id': service_id,
                    'name': service.get('name') or f"Service {service_id}",
                    'raw_data': service
                })
            elif 'proto' in service:
                # Service défini directement
                proto = service['proto']
                port = service.get('port')
                port_text = f":{port}" if port else ""
                
                normalized_services.append({
                    'type': 'proto',
                    'proto': proto,
                    'port': port,
                    'description': f"Proto {proto}{port_text}",
                    'raw_data': service
                })
        
        return normalized_services
    
    @staticmethod
    def extract_rule_hrefs(flows: List[Dict[str, Any]]) -> List[str]:
        """
        Extrait tous les hrefs uniques des règles à partir des flux de trafic.
        
        Args:
            flows: Liste des flux de trafic
            
        Returns:
            Liste des hrefs uniques des règles
        """
        unique_rule_hrefs = set()
        
        for flow in flows:
            # Différentes façons de trouver les hrefs des règles
            
            # 1. Chercher dans le champ 'rule_href'
            if isinstance(flow, dict) and 'rule_href' in flow and flow['rule_href']:
                # Le champ peut contenir plusieurs hrefs séparés par des points-virgules
                if isinstance(flow['rule_href'], str) and ';' in flow['rule_href']:
                    hrefs = [href.strip() for href in flow['rule_href'].split(';') if href.strip()]
                    for href in hrefs:
                        if href and href != 'N/A':
                            unique_rule_hrefs.add(href)
                else:
                    unique_rule_hrefs.add(flow['rule_href'])
            
            # 2. Chercher dans le champ 'rules'
            if isinstance(flow, dict) and 'rules' in flow:
                rules = flow['rules']
                RuleParser._extract_hrefs_from_rules(rules, unique_rule_hrefs)
            
            # 3. Chercher dans raw_data si présent
            if isinstance(flow, dict) and 'raw_data' in flow and flow['raw_data']:
                raw_data = flow['raw_data']
                
                # Si raw_data est une chaîne JSON, la parser
                if isinstance(raw_data, str):
                    try:
                        raw_data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        continue
                
                # Chercher dans rules de raw_data
                if isinstance(raw_data, dict) and 'rules' in raw_data:
                    rules = raw_data['rules']
                    RuleParser._extract_hrefs_from_rules(rules, unique_rule_hrefs)
        
        # Filtrer les valeurs non valides
        return [href for href in unique_rule_hrefs if href and href != 'N/A']
    
    @staticmethod
    def _extract_hrefs_from_rules(rules: Any, href_set: Set[str]):
        """
        Extrait les hrefs de règles depuis différentes structures et les ajoute à un set.
        
        Args:
            rules: Données des règles (dict ou list)
            href_set: Set pour stocker les hrefs uniques
        """
        if isinstance(rules, dict) and 'sec_policy' in rules:
            sec_policy = rules['sec_policy']
            if isinstance(sec_policy, dict) and 'href' in sec_policy:
                href_set.add(sec_policy['href'])
            elif isinstance(sec_policy, str):
                href_set.add(sec_policy)
        elif isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, dict) and 'href' in rule:
                    href_set.add(rule['href'])