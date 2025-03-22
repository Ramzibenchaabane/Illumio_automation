#illumio/formatters/rule_query_formatter.py
"""
Formatter pour les requêtes liées aux règles Illumio.

Ce module contient des méthodes pour construire les requêtes liées aux règles
de sécurité selon le format attendu par l'API Illumio PCE.
"""
from typing import Any, Dict, List, Optional, Union

from .request_formatter import RequestFormatter


class RuleQueryFormatter:
    """Classe pour formater les requêtes liées aux règles."""
    
    @staticmethod
    def format_rule_analysis_request(
        query_id: str,
        label_based_rules: bool = False,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Crée une requête pour l'analyse approfondie de règles.
        
        Args:
            query_id: Identifiant de la requête de trafic
            label_based_rules: Si True, utilise les règles basées sur les labels
            offset: Index de départ pour les résultats
            limit: Nombre maximum de résultats
            
        Returns:
            Paramètres de requête formatés pour l'API
        """
        return {
            'label_based_rules': 'true' if label_based_rules else 'false',
            'offset': offset,
            'limit': limit
        }
    
    @staticmethod
    def format_rule_download_request(
        query_id: str,
        offset: int = 0,
        limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Crée une requête pour télécharger les résultats d'analyse de règles.
        
        Args:
            query_id: Identifiant de la requête de trafic
            offset: Index de départ pour les résultats
            limit: Nombre maximum de résultats
            
        Returns:
            Paramètres de requête formatés pour l'API
        """
        return {
            'offset': offset,
            'limit': limit
        }
    
    @staticmethod
    def format_new_rule(
        rule_set_id: str,
        providers: List[Dict[str, Any]],
        consumers: List[Dict[str, Any]],
        ingress_services: List[Dict[str, Any]],
        description: Optional[str] = None,
        enabled: bool = True,
        resolve_labels_as: Optional[str] = None,
        sec_connect: bool = False,
        unscoped_consumers: bool = False
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle règle de sécurité.
        
        Args:
            rule_set_id: Identifiant du rule set contenant la règle
            providers: Liste des fournisseurs (sources)
            consumers: Liste des consommateurs (destinations)
            ingress_services: Liste des services
            description: Description de la règle (optionnel)
            enabled: Si la règle est activée (par défaut True)
            resolve_labels_as: Comment résoudre les labels (optionnel)
            sec_connect: Si SecureConnect est activé (par défaut False)
            unscoped_consumers: Si les consommateurs non scoped sont autorisés (par défaut False)
            
        Returns:
            Règle formatée selon les attentes de l'API
        """
        rule = {
            "enabled": enabled,
            "providers": providers,
            "consumers": consumers,
            "ingress_services": ingress_services,
            "sec_connect": sec_connect,
            "unscoped_consumers": unscoped_consumers
        }
        
        if description:
            rule["description"] = description
        
        if resolve_labels_as:
            rule["resolve_labels_as"] = resolve_labels_as
        
        return RequestFormatter.clean_empty_values(rule)
    
    @staticmethod
    def format_actor_as_workload(workload_href: str) -> Dict[str, Any]:
        """
        Formate un acteur (provider ou consumer) comme un workload.
        
        Args:
            workload_href: Href complet du workload
            
        Returns:
            Acteur formaté pour l'API
        """
        return {"workload": {"href": workload_href}}
    
    @staticmethod
    def format_actor_as_label(key: str, value: str) -> Dict[str, Any]:
        """
        Formate un acteur (provider ou consumer) comme un label.
        
        Args:
            key: Clé du label
            value: Valeur du label
            
        Returns:
            Acteur formaté pour l'API
        """
        return {"label": {"key": key, "value": value}}
    
    @staticmethod
    def format_actor_as_label_group(label_group_href: str) -> Dict[str, Any]:
        """
        Formate un acteur (provider ou consumer) comme un groupe de labels.
        
        Args:
            label_group_href: Href complet du groupe de labels
            
        Returns:
            Acteur formaté pour l'API
        """
        return {"label_group": {"href": label_group_href}}
    
    @staticmethod
    def format_actor_as_ip_list(ip_list_href: str) -> Dict[str, Any]:
        """
        Formate un acteur (provider ou consumer) comme une liste d'IPs.
        
        Args:
            ip_list_href: Href complet de la liste d'IPs
            
        Returns:
            Acteur formaté pour l'API
        """
        return {"ip_list": {"href": ip_list_href}}
    
    @staticmethod
    def format_actor_as_all_workloads() -> Dict[str, Any]:
        """
        Formate un acteur (provider ou consumer) comme tous les workloads gérés.
        
        Returns:
            Acteur formaté pour l'API
        """
        return {"actors": "ams"}
    
    @staticmethod
    def format_service_by_href(service_href: str) -> Dict[str, Any]:
        """
        Formate un service par sa référence href.
        
        Args:
            service_href: Href complet du service
            
        Returns:
            Service formaté pour l'API
        """
        return {"href": service_href}
    
    @staticmethod
    def format_service_by_proto_port(protocol: int, port: Optional[int] = None, to_port: Optional[int] = None) -> Dict[str, Any]:
        """
        Formate un service par protocole et port.
        
        Args:
            protocol: Numéro de protocole
            port: Port de début (optionnel)
            to_port: Port de fin (optionnel)
            
        Returns:
            Service formaté pour l'API
        """
        service = {"proto": protocol}
        
        if port is not None:
            service["port"] = port
        
        if to_port is not None:
            service["to_port"] = to_port
        
        return service