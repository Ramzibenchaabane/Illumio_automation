#illumio/formatters/request_formatter.py
"""
Formatter de base pour les requêtes vers l'API Illumio.

Ce module fournit une classe de base et des méthodes utilitaires pour 
construire les requêtes à envoyer à l'API Illumio PCE.
"""
from typing import Any, Dict, List, Optional, Union


class RequestFormatter:
    """Classe de base pour formater les requêtes vers l'API Illumio."""
    
    @staticmethod
    def format_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formate une requête générique vers l'API.
        
        Args:
            data: Données à formater
            
        Returns:
            Données formatées selon les attentes de l'API
        """
        # Classe de base qui ne fait qu'une validation minimale
        if not isinstance(data, dict):
            raise ValueError(f"Les données doivent être un dictionnaire, reçu {type(data)}")
        
        return data
    
    @staticmethod
    def clean_empty_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Supprime les valeurs None et les listes vides d'un dictionnaire.
        
        Args:
            data: Dictionnaire à nettoyer
            
        Returns:
            Dictionnaire sans valeurs vides
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        for key, value in data.items():
            # Récursion pour les dictionnaires imbriqués
            if isinstance(value, dict):
                cleaned_value = RequestFormatter.clean_empty_values(value)
                if cleaned_value:  # Ne pas inclure les dictionnaires vides
                    result[key] = cleaned_value
            # Récursion pour les listes contenant des dictionnaires
            elif isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = RequestFormatter.clean_empty_values(item)
                        if cleaned_item:  # Ne pas inclure les dictionnaires vides
                            cleaned_list.append(cleaned_item)
                    elif item is not None:  # Inclure les éléments non dictionnaires non None
                        cleaned_list.append(item)
                
                if cleaned_list:  # Ne pas inclure les listes vides
                    result[key] = cleaned_list
            # Inclure les valeurs non None
            elif value is not None:
                result[key] = value
        
        return result
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Vérifie que tous les champs requis sont présents dans les données.
        
        Args:
            data: Dictionnaire à vérifier
            required_fields: Liste des champs requis
            
        Returns:
            True si tous les champs requis sont présents, False sinon
        """
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        
        return True
    
    @staticmethod
    def validate_field_type(value: Any, expected_type: Union[type, tuple], field_name: str) -> None:
        """
        Vérifie qu'un champ est du type attendu.
        
        Args:
            value: Valeur à vérifier
            expected_type: Type ou tuple de types attendus
            field_name: Nom du champ pour les messages d'erreur
            
        Raises:
            TypeError: Si le type ne correspond pas
        """
        if not isinstance(value, expected_type):
            raise TypeError(f"Le champ '{field_name}' doit être de type {expected_type}, reçu {type(value)}")