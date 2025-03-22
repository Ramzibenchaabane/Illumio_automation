#illumio/formatters/workload_formatter.py
"""
Formatter pour les requêtes liées aux workloads Illumio.

Ce module contient des méthodes pour construire les requêtes liées aux workloads
selon le format attendu par l'API Illumio PCE.
"""
from typing import Any, Dict, List, Optional, Union

from .request_formatter import RequestFormatter


class WorkloadFormatter:
    """Classe pour formater les requêtes liées aux workloads."""
    
    @staticmethod
    def format_workload_filter(
        hostname: Optional[str] = None,
        name: Optional[str] = None,
        ip_address: Optional[str] = None,
        online: Optional[bool] = None,
        label_key: Optional[str] = None,
        label_value: Optional[str] = None,
        max_results: int = 500
    ) -> Dict[str, Any]:
        """
        Formate les paramètres de filtrage pour une requête de workloads.
        
        Args:
            hostname: Filtre par nom d'hôte (optionnel)
            name: Filtre par nom (optionnel)
            ip_address: Filtre par adresse IP (optionnel)
            online: Filtre par état online (optionnel)
            label_key: Filtre par clé de label (optionnel)
            label_value: Filtre par valeur de label (optionnel)
            max_results: Nombre maximum de résultats
            
        Returns:
            Paramètres de requête formatés pour l'API
        """
        params = {'max_results': max_results}
        
        if hostname:
            params['hostname'] = hostname
        
        if name:
            params['name'] = name
        
        if ip_address:
            params['ip_address'] = ip_address
        
        if online is not None:
            params['online'] = 'true' if online else 'false'
        
        if label_key:
            if label_value:
                params['labels'] = f'{label_key}:{label_value}'
            else:
                params['labels'] = label_key
        
        return params
    
    @staticmethod
    def format_new_workload(
        name: str,
        hostname: str,
        interfaces: List[Dict[str, Any]],
        description: Optional[str] = None,
        enforcement_mode: str = 'visibility_only',
        online: bool = True,
        labels: Optional[List[Dict[str, Any]]] = None,
        agent_type: str = 'server',
        os_type: str = 'linux',
        os_detail: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formate les données pour la création d'un nouveau workload.
        
        Args:
            name: Nom du workload
            hostname: Nom d'hôte du workload
            interfaces: Liste des interfaces réseau
            description: Description du workload (optionnel)
            enforcement_mode: Mode d'application (par défaut 'visibility_only')
            online: Si le workload est en ligne (par défaut True)
            labels: Liste des labels (optionnel)
            agent_type: Type d'agent (par défaut 'server')
            os_type: Type d'OS (par défaut 'linux')
            os_detail: Détails de l'OS (optionnel)
            
        Returns:
            Données formatées pour l'API
        """
        workload = {
            "name": name,
            "hostname": hostname,
            "interfaces": interfaces,
            "enforcement_mode": enforcement_mode,
            "online": online,
            "agent_type": agent_type,
            "os_type": os_type
        }
        
        if description:
            workload["description"] = description
        
        if labels:
            workload["labels"] = labels
        
        if os_detail:
            workload["os_detail"] = os_detail
        
        return RequestFormatter.clean_empty_values(workload)
    
    @staticmethod
    def format_interface(
        name: str,
        address: str,
        link_state: str = 'up',
        additional_addresses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Formate une interface réseau pour un workload.
        
        Args:
            name: Nom de l'interface (ex: 'eth0')
            address: Adresse IP principale
            link_state: État de la liaison (par défaut 'up')
            additional_addresses: Adresses IP supplémentaires (optionnel)
            
        Returns:
            Interface formatée pour l'API
        """
        interface = {
            "name": name,
            "address": address,
            "link_state": link_state
        }
        
        if additional_addresses:
            interface["addresses"] = additional_addresses
        
        return interface
    
    @staticmethod
    def format_label_reference(label_href: str) -> Dict[str, Any]:
        """
        Formate une référence à un label existant.
        
        Args:
            label_href: Href complet du label
            
        Returns:
            Label formaté pour l'API
        """
        return {"href": label_href}
    
    @staticmethod
    def format_workload_update(
        workload_href: str,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formate une requête de mise à jour d'un workload.
        
        Args:
            workload_href: Href complet du workload
            changes: Dictionnaire des modifications à appliquer
            
        Returns:
            Requête formatée pour l'API
        """
        # Seuls certains champs peuvent être mis à jour
        allowed_fields = [
            'name', 'hostname', 'description', 'enforcement_mode', 
            'online', 'labels', 'interfaces'
        ]
        
        update = {}
        for field, value in changes.items():
            if field in allowed_fields:
                update[field] = value
        
        return RequestFormatter.clean_empty_values(update)