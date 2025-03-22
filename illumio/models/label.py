# illumio/models/label.py
"""
Modèles de données pour les labels Illumio.

Ce module définit les classes de modèles typés pour représenter
les labels et dimensions de labels.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, ClassVar, Set


@dataclass
class Label:
    """Représente un label Illumio."""
    key: str
    value: str
    id: Optional[str] = None
    href: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Ensemble des clés de labels connues pour validation
    KNOWN_KEYS: ClassVar[Set[str]] = {'role', 'app', 'env', 'loc', 'custom'}
    
    def __post_init__(self):
        """Validation après initialisation."""
        if not self.key:
            raise ValueError("La clé du label ne peut pas être vide")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Label':
        """
        Crée une instance de Label à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du label
            
        Returns:
            Instance de Label
        
        Raises:
            ValueError: Si des données obligatoires sont manquantes
        """
        if not data:
            raise ValueError("Données de label manquantes")
        
        # Extraire l'ID à partir du href si nécessaire
        label_id = data.get('id')
        href = data.get('href')
        if not label_id and href:
            label_id = href.split('/')[-1]
        
        # Vérifier les champs obligatoires
        key = data.get('key')
        if not key:
            raise ValueError("Clé de label manquante")
        
        return cls(
            key=key,
            value=data.get('value', ''),
            id=label_id,
            href=href,
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant le label
        """
        result = {
            'key': self.key,
            'value': self.value
        }
        
        # Ajouter les champs optionnels s'ils existent
        if self.id:
            result['id'] = self.id
        
        if self.href:
            result['href'] = self.href
        
        if self.created_at:
            result['created_at'] = self.created_at
        
        if self.updated_at:
            result['updated_at'] = self.updated_at
        
        return result
    
    def __str__(self) -> str:
        """Représentation en chaîne."""
        return f"{self.key}:{self.value}"


@dataclass
class LabelDimension:
    """Représente une dimension de label (catégorie) dans Illumio."""
    key: str
    display_name: str
    allowed_values: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LabelDimension':
        """
        Crée une instance de LabelDimension à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la dimension
            
        Returns:
            Instance de LabelDimension
        """
        return cls(
            key=data.get('key', ''),
            display_name=data.get('display_name', ''),
            allowed_values=data.get('allowed_values')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant la dimension de label
        """
        result = {
            'key': self.key,
            'display_name': self.display_name
        }
        
        if self.allowed_values:
            result['allowed_values'] = self.allowed_values
        
        return result