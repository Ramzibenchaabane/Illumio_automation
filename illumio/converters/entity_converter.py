# illumio/converters/entity_converter.py
"""
Convertisseur de base pour les entités Illumio.

Ce module fournit une classe de base et des méthodes utilitaires pour convertir
les entités entre leur représentation en base de données et leur représentation en objet.
"""
import json
import sqlite3
from typing import Any, Dict, List, Optional, Union, Tuple, Type, TypeVar, Generic
import datetime

from ..exceptions import EntityConversionError, DatabaseConversionError

# Définir un type générique pour les modèles d'entité
T = TypeVar('T')

class EntityConverter(Generic[T]):
    """Classe de base pour la conversion d'entités."""
    
    @staticmethod
    def to_db_dict(entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit une entité pour stockage en base de données.
        
        Args:
            entity: Entité à convertir
            
        Returns:
            Dictionnaire prêt pour insertion en base de données
            
        Raises:
            EntityConversionError: Si l'entité ne peut pas être convertie
        """
        if not entity:
            return {}
            
        try:
            # Copier l'entité pour ne pas la modifier
            db_entity = entity.copy()
            
            # Conserver les données brutes pour référence
            if 'raw_data' not in db_entity:
                # Créer une copie sans les champs qui seraient dupliqués
                raw_data = {k: v for k, v in entity.items() if k != 'raw_data'}
                db_entity['raw_data'] = json.dumps(raw_data)
            elif isinstance(db_entity['raw_data'], dict):
                # Si raw_data est déjà un dictionnaire, le sérialiser
                db_entity['raw_data'] = json.dumps(db_entity['raw_data'])
            
            # Convertir les dates au format ISO si elles existent
            for date_field in ['created_at', 'updated_at', 'last_updated', 'completed_at']:
                if date_field in db_entity and not isinstance(db_entity[date_field], str):
                    if isinstance(db_entity[date_field], (datetime.datetime, datetime.date)):
                        db_entity[date_field] = db_entity[date_field].isoformat()
            
            return db_entity
        except Exception as e:
            raise EntityConversionError(f"Erreur lors de la conversion pour DB: {e}")
    
    @staticmethod
    def from_db_row(row: Union[sqlite3.Row, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convertit un enregistrement de base de données en entité.
        
        Args:
            row: Enregistrement de base de données (SQLite Row ou dict)
            
        Returns:
            Entité reconstruite
            
        Raises:
            DatabaseConversionError: Si l'enregistrement ne peut pas être converti
        """
        if not row:
            return {}
        
        try:
            # Convertir en dictionnaire si c'est un SQLite Row
            if isinstance(row, sqlite3.Row):
                entity = dict(row)
            else:
                entity = row.copy()
            
            # Traiter les données JSON
            if 'raw_data' in entity and isinstance(entity['raw_data'], str):
                try:
                    raw_data = json.loads(entity['raw_data'])
                    # Fusionner les données brutes avec l'entité, mais sans écraser les champs existants
                    for key, value in raw_data.items():
                        if key not in entity or entity[key] is None:
                            entity[key] = value
                except (json.JSONDecodeError, TypeError):
                    # Garder raw_data tel quel en cas d'erreur
                    pass
            
            return entity
        except Exception as e:
            raise DatabaseConversionError(f"Erreur lors de la conversion depuis DB: {e}")
    
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
    def prepare_for_insert(table_name: str, entity: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        Prépare une requête d'insertion SQL et ses paramètres.
        
        Args:
            table_name: Nom de la table
            entity: Entité à insérer
            
        Returns:
            Tuple (requête SQL, paramètres)
        """
        # Filtrer les champs qui ne sont pas None
        filtered_entity = {k: v for k, v in entity.items() if v is not None}
        columns = list(filtered_entity.keys())
        placeholders = ['?'] * len(columns)
        
        query = f'''
        INSERT OR REPLACE INTO {table_name} 
        ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        '''
        
        parameters = [filtered_entity[column] for column in columns]
        
        return query, parameters
    
    @staticmethod
    def convert_boolean_fields(entity: Dict[str, Any], boolean_fields: List[str]) -> Dict[str, Any]:
        """
        Convertit les champs booléens d'une entité en entiers pour la base de données.
        
        Args:
            entity: Entité à convertir
            boolean_fields: Liste des noms de champs booléens
            
        Returns:
            Entité avec les champs booléens convertis
        """
        result = entity.copy()
        
        for field in boolean_fields:
            if field in result:
                if result[field] is not None:
                    result[field] = 1 if result[field] else 0
        
        return result
    
    @staticmethod
    def normalize_db_values(entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise les valeurs de la base de données (convertit les None en valeurs par défaut appropriées).
        
        Args:
            entity: Entité à normaliser
            
        Returns:
            Entité normalisée
        """
        result = entity.copy()
        
        # Normaliser les chaînes vides
        for key, value in result.items():
            if value == '':
                result[key] = None
        
        return result
    
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
    
    @classmethod
    def to_model(cls, data: Dict[str, Any], model_class: Type[T]) -> T:
        """
        Convertit un dictionnaire en instance de modèle.
        
        Args:
            data: Dictionnaire de données
            model_class: Classe du modèle cible
            
        Returns:
            Instance du modèle
            
        Raises:
            EntityConversionError: Si la conversion échoue
        """
        try:
            # Utiliser la méthode from_dict du modèle si elle existe
            if hasattr(model_class, 'from_dict'):
                return model_class.from_dict(data)
            
            # Sinon, créer une instance avec les attributs du dictionnaire
            instance = model_class()
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            return instance
        except Exception as e:
            raise EntityConversionError(f"Erreur lors de la conversion en modèle: {e}")
    
    @classmethod
    def from_model(cls, model: T) -> Dict[str, Any]:
        """
        Convertit une instance de modèle en dictionnaire.
        
        Args:
            model: Instance du modèle
            
        Returns:
            Dictionnaire de données
            
        Raises:
            EntityConversionError: Si la conversion échoue
        """
        try:
            # Utiliser la méthode to_dict du modèle si elle existe
            if hasattr(model, 'to_dict') and callable(getattr(model, 'to_dict')):
                return model.to_dict()
            
            # Sinon, convertir les attributs en dictionnaire
            data = {}
            for key, value in model.__dict__.items():
                # Ignorer les attributs privés (commençant par _)
                if not key.startswith('_'):
                    data[key] = value
            
            return data
        except Exception as e:
            raise EntityConversionError(f"Erreur lors de la conversion depuis modèle: {e}")
    
    @staticmethod
    def json_serializable(obj: Any) -> Any:
        """
        Prépare un objet pour la sérialisation JSON en le convertissant en types de base.
        
        Args:
            obj: Objet à sérialiser
            
        Returns:
            Objet préparé pour la sérialisation JSON
        """
        if isinstance(obj, dict):
            return {k: EntityConverter.json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [EntityConverter.json_serializable(i) for i in obj]
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        elif hasattr(obj, '__dict__'):
            return EntityConverter.json_serializable(obj.__dict__)
        elif hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return EntityConverter.json_serializable(obj.to_dict())
        else:
            return str(obj)