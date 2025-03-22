#illumio/parsers/api_response_parser.py
"""
Parseur de base pour les réponses de l'API Illumio PCE.

Ce module fournit une classe de base et des méthodes utilitaires pour 
transformer les réponses brutes de l'API en structures de données normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union


class ApiResponseParser:
    """Classe de base pour parser les réponses de l'API Illumio."""

    @staticmethod
    def parse_response(response_data: Any) -> Any:
        """
        Parse une réponse générique de l'API.
        
        Args:
            response_data: Données brutes de la réponse API
            
        Returns:
            Données normalisées selon le type de réponse
        """
        if response_data is None:
            return None
            
        # Si la réponse est une chaîne JSON, la convertir en objet Python
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except json.JSONDecodeError:
                return response_data  # Retourner la chaîne si ce n'est pas du JSON valide
        
        # Traiter selon le type de données
        if isinstance(response_data, list):
            return [ApiResponseParser.parse_response(item) for item in response_data]
        elif isinstance(response_data, dict):
            # Si c'est une réponse d'erreur standard
            if 'error' in response_data and 'message' in response_data.get('error', {}):
                return {
                    'success': False,
                    'error': response_data['error']['message'],
                    'code': response_data.get('error', {}).get('code')
                }
            return response_data
        
        # Par défaut, retourner les données telles quelles
        return response_data
    
    @staticmethod
    def safe_json_loads(json_str: Optional[str], default: Any = None) -> Any:
        """
        Charge une chaîne JSON de manière sécurisée avec gestion d'erreur.
        
        Args:
            json_str: Chaîne JSON à parser
            default: Valeur par défaut à retourner en cas d'erreur
            
        Returns:
            Objet Python correspondant au JSON ou la valeur par défaut
        """
        if not json_str:
            return default
            
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return default
    
    @staticmethod
    def extract_id_from_href(href: Optional[str]) -> Optional[str]:
        """
        Extrait l'ID d'une ressource à partir de son href.
        
        Args:
            href: URL href complète (ex: '/api/v2/orgs/1/workloads/123')
            
        Returns:
            ID extrait ou None si impossible à extraire
        """
        if not href:
            return None
            
        # L'ID est généralement le dernier segment de l'URL
        return href.split('/')[-1] if '/' in href else href