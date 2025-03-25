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
            try:
                parsed_raw_data = json.loads(raw_data)
                if parsed_raw_data:
                    # Extraire les données de raw_data
                    raw_data = parsed_raw_data
            except json.JSONDecodeError:
                # En cas d'erreur de parsing, conserver raw_data tel quel
                pass
        elif isinstance(raw_data, dict):
            # raw_data est déjà un dictionnaire, pas besoin de le parser
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
        
        # Extraction du nom de la règle
        name = rule_data.get('name')
        if not name and isinstance(raw_data, dict):
            name = raw_data.get('name')
        
        # Extraire les scopes si disponibles dans les données brutes
        scopes = None
        if isinstance(raw_data, dict) and 'scopes' in raw_data:
            scopes = raw_data.get('scopes')
        
        # Construction de la règle normalisée
        normalized_rule = {
            'id': rule_id,
            'href': href,
            'name': name,
            'description': RuleParser._extract_description(rule_data, raw_data),
            'enabled': RuleParser._extract_enabled(rule_data, raw_data),
            'providers': RuleParser._parse_actors(rule_data.get('providers') or raw_data.get('providers', [])),
            'consumers': RuleParser._parse_actors(rule_data.get('consumers') or raw_data.get('consumers', [])),
            'services': RuleParser._parse_services(rule_data.get('ingress_services') or raw_data.get('ingress_services', [])),
            'resolve_labels_as': rule_data.get('resolve_labels_as') or raw_data.get('resolve_labels_as'),
            'sec_connect': rule_data.get('sec_connect') or raw_data.get('sec_connect', False),
            'unscoped_consumers': rule_data.get('unscoped_consumers') or raw_data.get('unscoped_consumers', False)
        }
        
        # Ajouter les scopes si disponibles
        if scopes:
            normalized_rule['scopes'] = RuleParser._parse_scopes(scopes)
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_rule:
            normalized_rule['raw_data'] = raw_data
        
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
    def _parse_scopes(scopes_data: Any) -> List[Dict[str, Any]]:
        """
        Parse les scopes d'un rule set.
        
        Args:
            scopes_data: Données brutes des scopes
            
        Returns:
            Liste des scopes normalisés avec informations de labels
        """
        if not scopes_data or not isinstance(scopes_data, list):
            return []
        
        normalized_scopes = []
        
        for scope_group in scopes_data:
            if not isinstance(scope_group, list):
                continue
                
            scope_labels = []
            for scope_item in scope_group:
                if not isinstance(scope_item, dict):
                    continue
                    
                if 'label' in scope_item and isinstance(scope_item['label'], dict):
                    label = scope_item['label']
                    key = label.get('key')
                    value = label.get('value')
                    href = label.get('href')
                    
                    if key is not None and value is not None:  # Vérification explicite pour éviter les valeurs vides
                        scope_labels.append({
                            'type': 'label',
                            'key': key,
                            'value': value,
                            'display': f"{key}:{value}",
                            'href': href,
                            'exclusion': scope_item.get('exclusion', False)
                        })
            
            if scope_labels:
                normalized_scopes.append(scope_labels)
        
        return normalized_scopes
    
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
                
                # Important: Conserver explicitement key et value dans l'acteur normalisé
                if key is not None and value is not None:  # Vérification explicite pour éviter les valeurs vides
                    actor_value = f"{key}:{value}"
                else:
                    # Si key ou value est absent/vide, on utilise ce qui est disponible
                    actor_value = key or value or "unknown_label"
                    
                # Créer l'acteur avec toutes les informations nécessaires
                normalized_actor = {
                    'type': actor_type,
                    'value': actor_value,
                    # Ajouter explicitement key et value comme attributs de premier niveau
                    'key': key,
                    'value': value,
                    'href': label.get('href'),
                    'raw_data': actor
                }
                
                normalized_actors.append(normalized_actor)
                continue
                
            elif 'label_group' in actor and isinstance(actor['label_group'], dict):
                actor_type = 'label_group'
                lg = actor['label_group']
                href = lg.get('href')
                name = lg.get('name')
                actor_value = name or ApiResponseParser.extract_id_from_href(href)
            elif 'workload' in actor and isinstance(actor['workload'], dict):
                actor_type = 'workload'
                wl = actor['workload']
                href = wl.get('href')
                name = wl.get('name')
                actor_value = name or ApiResponseParser.extract_id_from_href(href)
            elif 'ip_list' in actor and isinstance(actor['ip_list'], dict):
                actor_type = 'ip_list'
                ip = actor['ip_list']
                href = ip.get('href')
                name = ip.get('name')
                actor_value = name or ApiResponseParser.extract_id_from_href(href)
            
            if actor_type and not actor_type == 'label':  # Les labels sont déjà traités
                normalized_actor = {
                    'type': actor_type,
                    'value': actor_value,
                    'raw_data': actor
                }
                
                # Extraire l'ID ou le href si disponible pour références ultérieures
                if actor_type == 'label_group' and 'label_group' in actor:
                    href = actor['label_group'].get('href')
                    if href:
                        normalized_actor['href'] = href
                elif actor_type == 'workload' and 'workload' in actor:
                    href = actor['workload'].get('href')
                    if href:
                        normalized_actor['href'] = href
                elif actor_type == 'ip_list' and 'ip_list' in actor:
                    href = actor['ip_list'].get('href')
                    if href:
                        normalized_actor['href'] = href
                
                normalized_actors.append(normalized_actor)
        
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
                    'href': service.get('href'),
                    'raw_data': service
                })
            elif 'proto' in service:
                # Service défini directement
                proto = service['proto']
                port = service.get('port')
                to_port = service.get('to_port', port)
                port_text = f":{port}" if port else ""
                
                normalized_services.append({
                    'type': 'proto',
                    'proto': proto,
                    'port': port,
                    'to_port': to_port,
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