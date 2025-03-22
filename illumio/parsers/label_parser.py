#illumio/parsers/label_parser.py
"""
Parseur spécialisé pour les labels Illumio.

Ce module contient des méthodes pour transformer les données brutes des labels
provenant de l'API Illumio PCE en structures normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .api_response_parser import ApiResponseParser


class LabelParser:
    """Classe pour parser les labels Illumio."""
    
    @staticmethod
    def parse_label(label_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse un label individuel.
        
        Args:
            label_data: Données brutes du label
            
        Returns:
            Dictionnaire normalisé du label
        """
        # Si label_data est un objet ou contient des données JSON brutes
        if not isinstance(label_data, dict):
            if hasattr(label_data, '__dict__'):
                label_data = label_data.__dict__
            else:
                return {
                    'error': f"Type de label non supporté: {type(label_data)}",
                    'raw_data': str(label_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        raw_data = label_data.get('raw_data')
        if isinstance(raw_data, str):
            parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
            if parsed_raw_data:
                # Fusion des données
                source_data = {**parsed_raw_data, **label_data}
            else:
                source_data = label_data
        else:
            source_data = label_data
        
        # Extraction de l'ID du label
        label_id = source_data.get('id')
        if not label_id and 'href' in source_data:
            label_id = ApiResponseParser.extract_id_from_href(source_data['href'])
        
        # Construction du label normalisé
        normalized_label = {
            'id': label_id,
            'href': source_data.get('href'),
            'key': source_data.get('key'),
            'value': source_data.get('value'),
            'created_at': source_data.get('created_at'),
            'updated_at': source_data.get('updated_at')
        }
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_label:
            normalized_label['raw_data'] = json.dumps(source_data) if isinstance(source_data, dict) else str(source_data)
        
        return normalized_label
    
    @staticmethod
    def parse_labels(labels_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse une liste de labels.
        
        Args:
            labels_data: Liste des données brutes de labels
            
        Returns:
            Liste de dictionnaires normalisés
        """
        if not labels_data:
            return []
            
        normalized_labels = []
        for label in labels_data:
            try:
                normalized_label = LabelParser.parse_label(label)
                normalized_labels.append(normalized_label)
            except Exception as e:
                # Ajouter un label avec indication d'erreur
                normalized_labels.append({
                    'error': f"Erreur de parsing: {str(e)}",
                    'raw_data': json.dumps(label) if isinstance(label, dict) else str(label)
                })
        
        return normalized_labels
    
    @staticmethod
    def parse_label_dimensions(dimensions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les dimensions de labels (catégories).
        
        Args:
            dimensions_data: Liste des données brutes des dimensions
            
        Returns:
            Liste de dimensions normalisées
        """
        if not dimensions_data or not isinstance(dimensions_data, list):
            return []
        
        normalized_dimensions = []
        for dimension in dimensions_data:
            if not isinstance(dimension, dict):
                continue
            
            # Construction de la dimension normalisée
            normalized_dimension = {
                'key': dimension.get('key'),
                'display_name': dimension.get('display_name'),
                'allowed_values': dimension.get('allowed_values')
            }
            
            normalized_dimensions.append(normalized_dimension)
        
        return normalized_dimensions