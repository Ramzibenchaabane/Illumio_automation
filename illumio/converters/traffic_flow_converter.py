#illumio/converters/traffic_flow_converter.py
"""
Convertisseur pour les flux de trafic Illumio.

Ce module contient des méthodes spécialisées pour convertir les flux de trafic
entre leur représentation en base de données et leur représentation en objet.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .entity_converter import EntityConverter


class TrafficFlowConverter:
    """Classe pour la conversion des flux de trafic."""
    
    @staticmethod
    def to_db_dict(flow: Dict[str, Any], query_id: str) -> Dict[str, Any]:
        """
        Convertit un flux de trafic pour stockage en base de données.
        
        Args:
            flow: Flux à convertir
            query_id: ID de la requête associée
            
        Returns:
            Dictionnaire prêt pour insertion en base de données
        """
        if not flow:
            return {}
        
        # Créer une base pour l'entité de base de données
        db_flow = {
            'query_id': query_id,
            'src_ip': flow.get('src_ip'),
            'src_workload_id': flow.get('src_workload_id'),
            'dst_ip': flow.get('dst_ip'),
            'dst_workload_id': flow.get('dst_workload_id'),
            'service': flow.get('service_name'),
            'port': flow.get('service_port'),
            'protocol': flow.get('service_protocol'),
            'policy_decision': flow.get('policy_decision'),
            'first_detected': flow.get('first_detected'),
            'last_detected': flow.get('last_detected'),
            'num_connections': flow.get('num_connections'),
            'flow_direction': flow.get('flow_direction')
        }
        
        # MODIFICATION: Stocker tous les rule_href et rule_name comme un json
        # Extraire toutes les règles du flux
        rules_list = flow.get('rules', [])
        
        # Préparer les règles et stocker la liste complète
        if rules_list:
            # Stocker toutes les règles sous forme de JSON
            db_flow['rule_sec_policy'] = json.dumps(rules_list)
            
            # Maintenir aussi les champs individuels pour compatibilité ascendante
            # (en utilisant la première règle)
            if rules_list and isinstance(rules_list, list) and len(rules_list) > 0 and isinstance(rules_list[0], dict):
                first_rule = rules_list[0]
                db_flow['rule_href'] = first_rule.get('href')
                db_flow['rule_name'] = first_rule.get('name')
        else:
            # Cas alternatif: règles provenant directement du flow original
            # Format Legacy: Stocker les attributs rule_href et rule_name directement
            db_flow['rule_href'] = flow.get('rule_href')
            db_flow['rule_name'] = flow.get('rule_name')
            
            # Si rule_href est présent mais pas rule_sec_policy, créer une structure compatible
            if db_flow.get('rule_href') and not 'rule_sec_policy' in db_flow:
                rule_entry = {'href': db_flow['rule_href'], 'name': db_flow['rule_name']}
                db_flow['rule_sec_policy'] = json.dumps([rule_entry])
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in flow:
            # Créer une copie sans les champs qui seraient dupliqués
            raw_data = {k: v for k, v in flow.items() if k not in ('raw_data', 'excel_metadata')}
            db_flow['raw_data'] = json.dumps(raw_data)
        else:
            # Utiliser raw_data existant
            if isinstance(flow['raw_data'], dict):
                db_flow['raw_data'] = json.dumps(flow['raw_data'])
            else:
                db_flow['raw_data'] = flow['raw_data']
        
        return db_flow
    
    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un enregistrement de base de données en flux de trafic.
        
        Args:
            row: Enregistrement de base de données
            
        Returns:
            Flux de trafic reconstruit
        """
        if not row:
            return {}
        
        # Convertir d'abord avec le convertisseur générique
        flow = EntityConverter.from_db_row(row)
        
        # Reconstruire la structure du flux
        normalized_flow = {
            'src_ip': flow.get('src_ip'),
            'src_workload_id': flow.get('src_workload_id'),
            'dst_ip': flow.get('dst_ip'),
            'dst_workload_id': flow.get('dst_workload_id'),
            'service_name': flow.get('service'),
            'service_port': flow.get('port'),
            'service_protocol': flow.get('protocol'),
            'policy_decision': flow.get('policy_decision'),
            'first_detected': flow.get('first_detected'),
            'last_detected': flow.get('last_detected'),
            'num_connections': flow.get('num_connections'),
            'flow_direction': flow.get('flow_direction'),
            'rule_href': flow.get('rule_href'),
            'rule_name': flow.get('rule_name'),
            'query_id': flow.get('query_id')
        }
        
        # Reconstruire la structure src, dst, service
        src = {}
        if flow.get('src_ip'):
            src['ip'] = flow['src_ip']
        if flow.get('src_workload_id'):
            src['workload'] = {'href': f"/api/v2/orgs/1/workloads/{flow['src_workload_id']}"}
        
        dst = {}
        if flow.get('dst_ip'):
            dst['ip'] = flow['dst_ip']
        if flow.get('dst_workload_id'):
            dst['workload'] = {'href': f"/api/v2/orgs/1/workloads/{flow['dst_workload_id']}"}
        
        service = {}
        if flow.get('service'):
            service['name'] = flow['service']
        if flow.get('port'):
            service['port'] = flow['port']
        if flow.get('protocol'):
            service['proto'] = flow['protocol']
        
        # Ajouter les structures si elles contiennent des données
        if src:
            normalized_flow['src'] = src
        if dst:
            normalized_flow['dst'] = dst
        if service:
            normalized_flow['service'] = service
        
        # MODIFICATION: Reconstruire toutes les règles depuis rule_sec_policy
        rules = []
        
        if flow.get('rule_sec_policy'):
            try:
                rule_sec_policy = json.loads(flow['rule_sec_policy'])
                
                # Déterminer si c'est une liste ou un dictionnaire legacy
                if isinstance(rule_sec_policy, list):
                    # Format moderne: liste de règles
                    rules = rule_sec_policy
                elif isinstance(rule_sec_policy, dict):
                    # Format legacy: {"sec_policy": {...}}
                    rules = {'sec_policy': rule_sec_policy}
                else:
                    # Fallback
                    rules = [{'href': flow.get('rule_href'), 'name': flow.get('rule_name')}]
            except (json.JSONDecodeError, TypeError):
                # En cas d'erreur, utiliser le fallback
                if flow.get('rule_href'):
                    rules = [{'href': flow.get('rule_href'), 'name': flow.get('rule_name')}]
        elif flow.get('rule_href'):
            # Cas où rule_sec_policy n'existe pas mais rule_href oui
            rules = [{'href': flow.get('rule_href'), 'name': flow.get('rule_name')}]
            
        # Ajouter les règles à la sortie
        if rules:
            normalized_flow['rules'] = rules
        
        # Conserver raw_data
        if 'raw_data' in flow:
            normalized_flow['raw_data'] = flow['raw_data']
        
        return normalized_flow
    
    @staticmethod
    def to_db_query(query: Dict[str, Any], query_id: str, status: str = 'created') -> Dict[str, Any]:
        """
        Convertit une requête de trafic pour stockage en base de données.
        
        Args:
            query: Requête à convertir
            query_id: ID de la requête
            status: Statut initial de la requête
            
        Returns:
            Dictionnaire prêt pour insertion en base de données
        """
        if not query:
            return {}
        
        # Créer une base pour l'entité de base de données
        db_query = {
            'id': query_id,
            'query_name': query.get('query_name'),
            'status': status,
            'created_at': query.get('created_at') or 'CURRENT_TIMESTAMP',
            'raw_query': json.dumps(query)
        }
        
        return db_query
    
    @staticmethod
    def from_db_query(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un enregistrement de requête en objet de requête.
        
        Args:
            row: Enregistrement de base de données
            
        Returns:
            Objet de requête reconstruit
        """
        if not row:
            return {}
        
        # Convertir d'abord avec le convertisseur générique
        query = EntityConverter.from_db_row(row)
        
        # Extraire la requête brute si disponible
        raw_query = {}
        if 'raw_query' in query and isinstance(query['raw_query'], str):
            try:
                raw_query = json.loads(query['raw_query'])
            except json.JSONDecodeError:
                pass
        
        # Reconstruire la structure de la requête
        normalized_query = {
            'id': query.get('id'),
            'query_name': query.get('query_name'),
            'status': query.get('status'),
            'created_at': query.get('created_at'),
            'completed_at': query.get('completed_at'),
            'rules_status': query.get('rules_status'),
            'rules_completed_at': query.get('rules_completed_at'),
            'last_updated': query.get('last_updated')
        }
        
        # Ajouter les détails de la requête brute
        if raw_query:
            for key, value in raw_query.items():
                if key not in normalized_query:
                    normalized_query[key] = value
        
        return normalized_query