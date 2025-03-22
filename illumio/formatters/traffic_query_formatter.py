#illumio/formatters/traffic_query_formatter.py
"""
Formatter pour les requêtes d'analyse de trafic Illumio.

Ce module contient des méthodes pour construire les requêtes d'analyse de trafic
selon le format attendu par l'API Illumio PCE.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from .request_formatter import RequestFormatter


class TrafficQueryFormatter:
    """Classe pour formater les requêtes d'analyse de trafic."""
    
    @staticmethod
    def format_default_query(
        query_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 10000
    ) -> Dict[str, Any]:
        """
        Crée une requête d'analyse de trafic par défaut.
        
        Args:
            query_name: Nom de la requête (optionnel)
            start_date: Date de début au format YYYY-MM-DD (optionnel)
            end_date: Date de fin au format YYYY-MM-DD (optionnel)
            max_results: Nombre maximum de résultats
            
        Returns:
            Requête formatée selon les attentes de l'API
        """
        # Générer un nom par défaut si non fourni
        if not query_name:
            query_name = f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Définir les dates par défaut si non fournies
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Structure de base d'une requête de trafic
        query = {
            "query_name": query_name,
            "start_date": start_date,
            "end_date": end_date,
            "sources_destinations_query_op": "and",
            "sources": {
                "include": [
                    [{"actors": "ams"}]
                ],
                "exclude": []
            },
            "destinations": {
                "include": [
                    [{"actors": "ams"}]
                ],
                "exclude": []
            },
            "services": {
                "include": [],
                "exclude": []
            },
            "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
            "max_results": max_results,
            "exclude_workloads_from_ip_list_query": True
        }
        
        return query
    
    @staticmethod
    def format_specific_flow_query(
        source_ip: str,
        dest_ip: str,
        protocol: int,
        port: Optional[int] = None,
        query_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 1000
    ) -> Dict[str, Any]:
        """
        Crée une requête pour un flux spécifique entre source et destination.
        
        Args:
            source_ip: Adresse IP source
            dest_ip: Adresse IP destination
            protocol: Protocole IP
            port: Port TCP/UDP (optionnel)
            query_name: Nom de la requête (optionnel)
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            max_results: Nombre maximum de résultats
            
        Returns:
            Requête formatée selon les attentes de l'API
        """
        # Générer un nom par défaut si non fourni
        if not query_name:
            query_name = f"Flow_{source_ip}_to_{dest_ip}_{protocol}"
            if port:
                query_name += f"_port{port}"
        
        # Définir les dates par défaut si non fournies
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Construire le filtre de service
        service_include = [{"proto": protocol}]
        if port is not None:
            service_include = [{"proto": protocol, "port": port}]
        
        # Structure de la requête pour un flux spécifique
        query = {
            "query_name": query_name,
            "start_date": start_date,
            "end_date": end_date,
            "sources_destinations_query_op": "and",
            "sources": {
                "include": [
                    [{"ip_address": source_ip}]
                ],
                "exclude": []
            },
            "destinations": {
                "include": [
                    [{"ip_address": dest_ip}]
                ],
                "exclude": []
            },
            "services": {
                "include": service_include,
                "exclude": []
            },
            "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
            "max_results": max_results
        }
        
        return query
    
    @staticmethod
    def format_custom_query(
        query_name: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        destinations: Optional[List[Dict[str, Any]]] = None,
        services: Optional[List[Dict[str, Any]]] = None,
        policy_decisions: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 10000,
    ) -> Dict[str, Any]:
        """
        Crée une requête personnalisée avec les filtres spécifiés.
        
        Args:
            query_name: Nom de la requête (optionnel)
            sources: Liste de filtres de sources (optionnel)
            destinations: Liste de filtres de destinations (optionnel)
            services: Liste de filtres de services (optionnel)
            policy_decisions: Liste des décisions de politique (optionnel)
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            max_results: Nombre maximum de résultats
            
        Returns:
            Requête formatée selon les attentes de l'API
        """
        # Commencer avec une requête par défaut
        query = TrafficQueryFormatter.format_default_query(
            query_name=query_name,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results
        )
        
        # Mettre à jour les filtres si spécifiés
        if sources:
            # S'assurer que chaque source est correctement formatée
            formatted_sources = []
            for source in sources:
                # Chaque élément de source doit être dans un tableau
                if isinstance(source, dict):
                    formatted_sources.append([source])
                elif isinstance(source, list):
                    formatted_sources.append(source)
            
            if formatted_sources:
                query["sources"]["include"] = formatted_sources
        
        if destinations:
            # S'assurer que chaque destination est correctement formatée
            formatted_destinations = []
            for destination in destinations:
                # Chaque élément de destination doit être dans un tableau
                if isinstance(destination, dict):
                    formatted_destinations.append([destination])
                elif isinstance(destination, list):
                    formatted_destinations.append(destination)
            
            if formatted_destinations:
                query["destinations"]["include"] = formatted_destinations
        
        if services:
            # Les services sont directement une liste de dictionnaires
            query["services"]["include"] = services
        
        if policy_decisions:
            query["policy_decisions"] = policy_decisions
        
        return query
    
    @staticmethod
    def validate_query(query: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valide une requête d'analyse de trafic.
        
        Args:
            query: Requête à valider
            
        Returns:
            Tuple (valide, message), où valide est un booléen et message est une chaîne
        """
        required_fields = ['query_name', 'start_date', 'end_date', 'sources', 'destinations']
        
        # Vérifier les champs requis
        for field in required_fields:
            if field not in query:
                return False, f"Champ requis manquant: {field}"
        
        # Vérifier le format des dates
        date_fields = ['start_date', 'end_date']
        for field in date_fields:
            if field in query:
                try:
                    # Vérifier le format de date YYYY-MM-DD
                    datetime.strptime(query[field], '%Y-%m-%d')
                except ValueError:
                    return False, f"Format de date invalide pour {field}: {query[field]}"
        
        # Vérifier la structure des sources et destinations
        for field in ['sources', 'destinations']:
            if field in query:
                if not isinstance(query[field], dict) or 'include' not in query[field]:
                    return False, f"Format invalide pour {field}"
        
        # Vérifier les services si présents
        if 'services' in query and 'include' in query['services']:
            services = query['services']['include']
            if not isinstance(services, list):
                return False, "Les services doivent être une liste"
            
            for service in services:
                if not isinstance(service, dict):
                    return False, "Chaque service doit être un dictionnaire"
                
                if 'proto' not in service:
                    return False, "Chaque service doit avoir un protocole"
        
        return True, "Requête valide"