#illumio/parsers/workload_parser.py
"""
Parseur spécialisé pour les workloads Illumio.

Ce module contient des méthodes pour transformer les données brutes des workloads
provenant de l'API Illumio PCE en structures normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .api_response_parser import ApiResponseParser


class WorkloadParser:
    """Classe pour parser les workloads Illumio."""
    
    @staticmethod
    def parse_workload(workload_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse un workload individuel.
        
        Args:
            workload_data: Données brutes du workload
            
        Returns:
            Dictionnaire normalisé du workload
        """
        # Si workload_data est un objet ou contient des données JSON brutes
        if not isinstance(workload_data, dict):
            if hasattr(workload_data, '__dict__'):
                workload_data = workload_data.__dict__
            else:
                return {
                    'error': f"Type de workload non supporté: {type(workload_data)}",
                    'raw_data': str(workload_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        raw_data = workload_data.get('raw_data')
        if isinstance(raw_data, str):
            parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
            if parsed_raw_data:
                # Fusion des données
                source_data = {**parsed_raw_data, **workload_data}
            else:
                source_data = workload_data
        else:
            source_data = workload_data
        
        # Extraction de l'ID du workload
        workload_id = source_data.get('id')
        if not workload_id and 'href' in source_data:
            workload_id = ApiResponseParser.extract_id_from_href(source_data['href'])
        
        # Extraction du statut online
        online = source_data.get('online')
        if isinstance(online, str):
            online = online.lower() == 'true'
        else:
            online = bool(online)
        
        # Construction du workload normalisé
        normalized_workload = {
            'id': workload_id,
            'href': source_data.get('href'),
            'name': source_data.get('name'),
            'hostname': source_data.get('hostname'),
            'description': source_data.get('description'),
            'public_ip': source_data.get('public_ip'),
            'online': online,
            'os_detail': source_data.get('os_detail'),
            'service_provider': source_data.get('service_provider'),
            'data_center': source_data.get('data_center'),
            'data_center_zone': source_data.get('data_center_zone'),
            'interfaces': WorkloadParser._parse_interfaces(source_data.get('interfaces', [])),
            'labels': WorkloadParser._parse_labels(source_data.get('labels', []))
        }
        
        # Gestion de enforcement_mode (qui peut être un objet ou une chaîne)
        enforcement_mode = source_data.get('enforcement_mode')
        if isinstance(enforcement_mode, dict) and 'mode' in enforcement_mode:
            normalized_workload['enforcement_mode'] = enforcement_mode['mode']
        else:
            normalized_workload['enforcement_mode'] = enforcement_mode
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_workload:
            normalized_workload['raw_data'] = json.dumps(source_data) if isinstance(source_data, dict) else str(source_data)
        
        return normalized_workload
    
    @staticmethod
    def parse_workloads(workloads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse une liste de workloads.
        
        Args:
            workloads_data: Liste des données brutes de workloads
            
        Returns:
            Liste de dictionnaires normalisés
        """
        if not workloads_data:
            return []
            
        normalized_workloads = []
        for workload in workloads_data:
            try:
                normalized_workload = WorkloadParser.parse_workload(workload)
                normalized_workloads.append(normalized_workload)
            except Exception as e:
                # Ajouter un workload avec indication d'erreur
                normalized_workloads.append({
                    'error': f"Erreur de parsing: {str(e)}",
                    'raw_data': json.dumps(workload) if isinstance(workload, dict) else str(workload)
                })
        
        return normalized_workloads
    
    @staticmethod
    def _parse_interfaces(interfaces_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les interfaces réseau d'un workload.
        
        Args:
            interfaces_data: Données brutes des interfaces
            
        Returns:
            Liste d'interfaces normalisées
        """
        if not interfaces_data or not isinstance(interfaces_data, list):
            return []
        
        normalized_interfaces = []
        for interface in interfaces_data:
            if not isinstance(interface, dict):
                continue
            
            # Extraction des adresses IP
            ip_addresses = []
            if 'address' in interface:
                ip_addresses.append(interface['address'])
            
            if 'addresses' in interface and isinstance(interface['addresses'], list):
                ip_addresses.extend(interface['addresses'])
            
            # Construction de l'interface normalisée
            normalized_interface = {
                'name': interface.get('name'),
                'link_state': interface.get('link_state'),
                'addresses': ip_addresses
            }
            
            normalized_interfaces.append(normalized_interface)
        
        return normalized_interfaces
    
    @staticmethod
    def _parse_labels(labels_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les labels d'un workload.
        
        Args:
            labels_data: Données brutes des labels
            
        Returns:
            Liste de labels normalisés
        """
        if not labels_data or not isinstance(labels_data, list):
            return []
        
        normalized_labels = []
        for label in labels_data:
            if not isinstance(label, dict):
                continue
            
            # Extraction de l'ID du label
            label_id = label.get('id')
            if not label_id and 'href' in label:
                label_id = ApiResponseParser.extract_id_from_href(label['href'])
            
            # Construction du label normalisé
            normalized_label = {
                'id': label_id,
                'href': label.get('href'),
                'key': label.get('key'),
                'value': label.get('value')
            }
            
            normalized_labels.append(normalized_label)
        
        return normalized_labels