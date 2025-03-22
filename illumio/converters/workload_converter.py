#illumio/converters/workload_converter.py
"""
Convertisseur pour les workloads Illumio.

Ce module contient des méthodes spécialisées pour convertir les workloads
entre leur représentation en base de données et leur représentation en objet.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .entity_converter import EntityConverter


class WorkloadConverter:
    """Classe pour la conversion des workloads."""
    
    @staticmethod
    def to_db_dict(workload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un workload pour stockage en base de données.
        
        Args:
            workload: Workload à convertir
            
        Returns:
            Dictionnaire prêt pour insertion en base de données
        """
        if not workload:
            return {}
        
        # Extraire l'ID du workload
        workload_id = workload.get('id')
        if not workload_id and 'href' in workload:
            # Extraire l'ID depuis l'URL
            href = workload['href']
            workload_id = href.split('/')[-1] if href else None
        
        # Créer une base pour l'entité de base de données
        db_workload = {
            'id': workload_id,
            'name': workload.get('name'),
            'hostname': workload.get('hostname'),
            'description': workload.get('description'),
            'public_ip': workload.get('public_ip'),
            'online': 1 if workload.get('online') else 0,
            'os_detail': workload.get('os_detail'),
            'service_provider': workload.get('service_provider'),
            'data_center': workload.get('data_center'),
            'data_center_zone': workload.get('data_center_zone'),
            'raw_data': json.dumps(workload) if isinstance(workload, dict) else workload
        }
        
        # Traiter enforcement_mode qui peut être un objet ou une chaîne
        enforcement_mode = workload.get('enforcement_mode')
        if isinstance(enforcement_mode, dict) and 'mode' in enforcement_mode:
            db_workload['enforcement_mode'] = enforcement_mode['mode']
        else:
            db_workload['enforcement_mode'] = enforcement_mode
        
        return db_workload
    
    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un enregistrement de base de données en workload.
        
        Args:
            row: Enregistrement de base de données
            
        Returns:
            Workload reconstruit
        """
        if not row:
            return {}
        
        # Convertir d'abord avec le convertisseur générique
        workload = EntityConverter.from_db_row(row)
        
        # Reconstruire la structure du workload
        normalized_workload = {
            'id': workload.get('id'),
            'name': workload.get('name'),
            'hostname': workload.get('hostname'),
            'description': workload.get('description'),
            'public_ip': workload.get('public_ip'),
            'online': bool(workload.get('online')),
            'os_detail': workload.get('os_detail'),
            'service_provider': workload.get('service_provider'),
            'data_center': workload.get('data_center'),
            'data_center_zone': workload.get('data_center_zone'),
            'enforcement_mode': workload.get('enforcement_mode')
        }
        
        # Reconstruire le href si nécessaire
        if 'id' in normalized_workload:
            workload_id = normalized_workload['id']
            normalized_workload['href'] = f"/api/v2/orgs/1/workloads/{workload_id}"
        
        return normalized_workload
    
    @staticmethod
    def extract_workload_labels(workload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrait les associations workload-label pour stockage en base de données.
        
        Args:
            workload: Workload contenant des labels
            
        Returns:
            Liste des associations workload-label
        """
        if not workload or 'labels' not in workload or not isinstance(workload['labels'], list):
            return []
        
        # Extraire l'ID du workload
        workload_id = workload.get('id')
        if not workload_id and 'href' in workload:
            href = workload['href']
            workload_id = href.split('/')[-1] if href else None
        
        if not workload_id:
            return []
        
        # Extraire les associations workload-label
        associations = []
        for label in workload['labels']:
            if not isinstance(label, dict):
                continue
            
            # Extraire l'ID du label
            label_id = label.get('id')
            if not label_id and 'href' in label:
                href = label['href']
                label_id = href.split('/')[-1] if href else None
            
            if label_id:
                associations.append({
                    'workload_id': workload_id,
                    'label_id': label_id
                })
        
        return associations
    
    @staticmethod
    def extract_interfaces(workload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrait les interfaces réseau d'un workload pour stockage en base de données.
        
        Args:
            workload: Workload contenant des interfaces
            
        Returns:
            Liste des interfaces
        """
        if not workload or 'interfaces' not in workload or not isinstance(workload['interfaces'], list):
            return []
        
        # Extraire l'ID du workload
        workload_id = workload.get('id')
        if not workload_id and 'href' in workload:
            href = workload['href']
            workload_id = href.split('/')[-1] if href else None
        
        if not workload_id:
            return []
        
        # Extraire les interfaces
        db_interfaces = []
        for interface in workload['interfaces']:
            if not isinstance(interface, dict):
                continue
            
            # Base de l'interface
            db_interface = {
                'workload_id': workload_id,
                'name': interface.get('name'),
                'link_state': interface.get('link_state', 'up'),
                'address': interface.get('address')
            }
            
            # Convertir les adresses supplémentaires en JSON
            if 'addresses' in interface and isinstance(interface['addresses'], list):
                db_interface['addresses'] = json.dumps(interface['addresses'])
            
            db_interfaces.append(db_interface)
        
        return db_interfaces