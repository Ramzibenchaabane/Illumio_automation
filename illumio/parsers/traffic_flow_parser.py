#illumio/parsers/traffic_flow_parser.py
"""
Parseur spécialisé pour les flux de trafic Illumio.

Ce module contient des méthodes pour transformer les données brutes de flux
de trafic provenant de l'API Illumio PCE en structures normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .api_response_parser import ApiResponseParser
from .rule_parser import RuleParser


class TrafficFlowParser:
    """Classe pour parser les flux de trafic Illumio."""
    
    @staticmethod
    def parse_flow(flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse un flux de trafic individuel.
        
        Args:
            flow_data: Données brutes du flux
            
        Returns:
            Dictionnaire normalisé du flux
        """
        # Si flow_data est un objet avec raw_data, extraire raw_data
        if not isinstance(flow_data, dict):
            if hasattr(flow_data, 'get') and callable(flow_data.get):
                # Si c'est un objet qui supporte la méthode get()
                pass  # On continue avec cet objet
            elif hasattr(flow_data, '__dict__'):
                # Convertir l'objet en dictionnaire
                flow_data = flow_data.__dict__
            elif hasattr(flow_data, 'raw_data'):
                # Si l'objet a un attribut raw_data
                raw_data = flow_data.raw_data
                if isinstance(raw_data, str):
                    # Si raw_data est une chaîne JSON, la parser
                    flow_data = ApiResponseParser.safe_json_loads(raw_data, {})
                else:
                    flow_data = raw_data
            else:
                # Impossible de traiter ce type de flux
                return {
                    'error': f"Type de flux non supporté: {type(flow_data)}",
                    'raw_data': str(flow_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        if isinstance(flow_data, dict) and 'raw_data' in flow_data and isinstance(flow_data['raw_data'], str):
            raw_data = ApiResponseParser.safe_json_loads(flow_data['raw_data'], {})
            if raw_data:
                # Fusionner avec les données existantes (raw_data prend priorité)
                # Mais d'abord, sauvegarder flow_data original pour des champs spécifiques
                original_data = {
                    'src_ip': flow_data.get('src_ip'),
                    'dst_ip': flow_data.get('dst_ip'),
                    'service_name': flow_data.get('service_name'),
                    'rule_href': flow_data.get('rule_href'),
                    'rule_name': flow_data.get('rule_name')
                }
                flow_data = {**raw_data, **flow_data}
                
                # Restaurer les champs spécifiques qui auraient été écrasés mais qui ont une valeur
                for key, value in original_data.items():
                    if value is not None and key not in flow_data:
                        flow_data[key] = value
        
        # Extraction normalisée des données source
        src_data = TrafficFlowParser._parse_endpoint(
            flow_data.get('src', {}),
            fallback_ip=flow_data.get('src_ip'),
            fallback_workload_id=flow_data.get('src_workload_id')
        )
        
        # Extraction normalisée des données destination
        dst_data = TrafficFlowParser._parse_endpoint(
            flow_data.get('dst', {}),
            fallback_ip=flow_data.get('dst_ip'),
            fallback_workload_id=flow_data.get('dst_workload_id')
        )
        
        # Extraction normalisée des données de service
        service_data = TrafficFlowParser._parse_service(
            flow_data.get('service', {}),
            fallback_name=flow_data.get('service_name'),
            fallback_port=flow_data.get('service_port'),
            fallback_proto=flow_data.get('service_protocol') or flow_data.get('protocol')
        )
        
        # Extraction normalisée des données de règle
        rule_data = {}
        if 'rule_href' in flow_data or 'rule_name' in flow_data:
            rule_data = {
                'href': flow_data.get('rule_href'),
                'name': flow_data.get('rule_name')
            }
        elif 'rules' in flow_data:
            rule_data = RuleParser.parse_rule_reference(flow_data['rules'])
        
        # Construction du flux normalisé
        normalized_flow = {
            'src_ip': src_data.get('ip'),
            'src_workload_id': src_data.get('workload_id'),
            'dst_ip': dst_data.get('ip'),
            'dst_workload_id': dst_data.get('workload_id'),
            'service_name': service_data.get('name'),
            'service_port': service_data.get('port'),
            'service_protocol': service_data.get('proto'),
            'policy_decision': flow_data.get('policy_decision'),
            'flow_direction': flow_data.get('flow_direction'),
            'num_connections': flow_data.get('num_connections'),
            'first_detected': flow_data.get('first_detected') or 
                             flow_data.get('timestamp_range', {}).get('first_detected'),
            'last_detected': flow_data.get('last_detected') or
                            flow_data.get('timestamp_range', {}).get('last_detected'),
            'rule_href': rule_data.get('href'),
            'rule_name': rule_data.get('name')
        }
        
        # Si des métadonnées Excel existent, les préserver
        if 'excel_metadata' in flow_data:
            normalized_flow['excel_metadata'] = flow_data['excel_metadata']
        
        # Conserver les données brutes pour référence si nécessaire
        if 'raw_data' not in flow_data:
            # Si les données brutes ne sont pas déjà présentes, les ajouter
            normalized_flow['raw_data'] = json.dumps(flow_data)
        else:
            # Sinon, conserver les données brutes existantes
            normalized_flow['raw_data'] = flow_data['raw_data']
        
        return normalized_flow
    
    @staticmethod
    def parse_flows(flows_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse une liste de flux de trafic.
        
        Args:
            flows_data: Liste des données brutes de flux
            
        Returns:
            Liste de dictionnaires normalisés
        """
        if not flows_data:
            return []
            
        normalized_flows = []
        for flow in flows_data:
            try:
                normalized_flow = TrafficFlowParser.parse_flow(flow)
                normalized_flows.append(normalized_flow)
            except Exception as e:
                # Ajouter un flux avec indication d'erreur
                normalized_flows.append({
                    'error': f"Erreur de parsing: {str(e)}",
                    'raw_data': json.dumps(flow) if isinstance(flow, dict) else str(flow)
                })
        
        return normalized_flows
    
    @staticmethod
    def _parse_endpoint(endpoint_data: Dict[str, Any], fallback_ip: Optional[str] = None,
                      fallback_workload_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse les données d'un point de terminaison (source ou destination).
        
        Args:
            endpoint_data: Données brutes du point de terminaison
            fallback_ip: IP à utiliser si non trouvée dans endpoint_data
            fallback_workload_id: ID de workload à utiliser si non trouvé
            
        Returns:
            Dictionnaire normalisé du point de terminaison
        """
        # Initialiser avec les valeurs par défaut
        result = {
            'ip': None,
            'workload_id': None
        }
        
        # Si les données sont un dictionnaire valide
        if isinstance(endpoint_data, dict):
            # Extraction de l'IP
            result['ip'] = endpoint_data.get('ip')
            
            # Extraction de l'ID de workload
            workload = endpoint_data.get('workload', {})
            if isinstance(workload, dict) and 'href' in workload:
                result['workload_id'] = ApiResponseParser.extract_id_from_href(workload['href'])
        
        # Appliquer les fallbacks si nécessaire
        if result['ip'] is None and fallback_ip is not None:
            result['ip'] = fallback_ip
        
        if result['workload_id'] is None and fallback_workload_id is not None:
            result['workload_id'] = fallback_workload_id
        
        return result
    
    @staticmethod
    def _parse_service(service_data: Dict[str, Any], fallback_name: Optional[str] = None,
                     fallback_port: Optional[int] = None, fallback_proto: Optional[int] = None) -> Dict[str, Any]:
        """
        Parse les données d'un service.
        
        Args:
            service_data: Données brutes du service
            fallback_name: Nom à utiliser si non trouvé dans service_data
            fallback_port: Port à utiliser si non trouvé
            fallback_proto: Protocole à utiliser si non trouvé
            
        Returns:
            Dictionnaire normalisé du service
        """
        # Initialiser avec les valeurs par défaut
        result = {
            'name': None,
            'port': None,
            'proto': None
        }
        
        # Si les données sont un dictionnaire valide
        if isinstance(service_data, dict):
            # Récupérer le nom directement
            result['name'] = service_data.get('name')
            
            # Vérifier si port et proto sont directement au niveau racine
            direct_port = service_data.get('port')
            direct_proto = service_data.get('proto')
            
            if direct_port is not None:
                result['port'] = direct_port
            if direct_proto is not None:
                result['proto'] = direct_proto
            
            # Vérifier si service_ports existe et contient des informations
            service_ports = service_data.get('service_ports', [])
            if service_ports and isinstance(service_ports, list) and len(service_ports) > 0:
                first_port = service_ports[0]
                if isinstance(first_port, dict):
                    # N'écraser les valeurs que si elles sont encore None
                    if result['port'] is None:
                        result['port'] = first_port.get('port')
                    if result['proto'] is None:
                        result['proto'] = first_port.get('proto')
            
            # Extraire aussi l'ID du service si disponible via href
            if 'href' in service_data:
                service_id = ApiResponseParser.extract_id_from_href(service_data['href'])
                result['service_id'] = service_id
        elif isinstance(service_data, str):
            # Si c'est une chaîne, l'utiliser comme nom
            result['name'] = service_data
        
        # Appliquer les fallbacks si nécessaire
        if result['name'] is None and fallback_name is not None:
            result['name'] = fallback_name
        
        if result['port'] is None and fallback_port is not None:
            try:
                result['port'] = int(fallback_port)
            except (ValueError, TypeError):
                pass
        
        if result['proto'] is None and fallback_proto is not None:
            try:
                result['proto'] = int(fallback_proto)
            except (ValueError, TypeError):
                pass
        
        return result