#illumio/parsers/label_group_parser.py
"""
Parseur spécialisé pour les groupes de labels Illumio.

Ce module contient des méthodes pour transformer les données brutes des groupes de labels
provenant de l'API Illumio PCE en structures normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .api_response_parser import ApiResponseParser


class LabelGroupParser:
    """Classe pour parser les groupes de labels Illumio."""
    
    @staticmethod
    def parse_label_group(label_group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse un groupe de labels individuel.
        
        Args:
            label_group_data: Données brutes du groupe de labels
            
        Returns:
            Dictionnaire normalisé du groupe de labels
        """
        # Si label_group_data est un objet ou contient des données JSON brutes
        if not isinstance(label_group_data, dict):
            if hasattr(label_group_data, '__dict__'):
                label_group_data = label_group_data.__dict__
            else:
                return {
                    'error': f"Type de groupe de labels non supporté: {type(label_group_data)}",
                    'raw_data': str(label_group_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        raw_data = label_group_data.get('raw_data')
        if isinstance(raw_data, str):
            parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
            if parsed_raw_data:
                # Fusion des données
                source_data = {**parsed_raw_data, **label_group_data}
            else:
                source_data = label_group_data
        else:
            source_data = label_group_data
        
        # Extraction de l'ID du groupe de labels
        label_group_id = source_data.get('id')
        if not label_group_id and 'href' in source_data:
            label_group_id = ApiResponseParser.extract_id_from_href(source_data['href'])
        
        # Construction du groupe de labels normalisé
        normalized_label_group = {
            'id': label_group_id,
            'href': source_data.get('href'),
            'name': source_data.get('name'),
            'description': source_data.get('description'),
            'created_at': source_data.get('created_at'),
            'updated_at': source_data.get('updated_at'),
            'members': LabelGroupParser._parse_members(source_data.get('members', []) or 
                                                     source_data.get('sub_groups', []) or
                                                     source_data.get('labels', []))
        }
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_label_group:
            normalized_label_group['raw_data'] = json.dumps(source_data) if isinstance(source_data, dict) else str(source_data)
        
        return normalized_label_group
    
    @staticmethod
    def parse_label_groups(label_groups_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse une liste de groupes de labels.
        
        Args:
            label_groups_data: Liste des données brutes de groupes de labels
            
        Returns:
            Liste de dictionnaires normalisés
        """
        if not label_groups_data:
            return []
            
        normalized_label_groups = []
        for label_group in label_groups_data:
            try:
                normalized_label_group = LabelGroupParser.parse_label_group(label_group)
                normalized_label_groups.append(normalized_label_group)
            except Exception as e:
                # Ajouter un groupe de labels avec indication d'erreur
                normalized_label_groups.append({
                    'error': f"Erreur de parsing: {str(e)}",
                    'raw_data': json.dumps(label_group) if isinstance(label_group, dict) else str(label_group)
                })
        
        return normalized_label_groups
    
    @staticmethod
    def _parse_members(members_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les membres d'un groupe de labels.
        
        Args:
            members_data: Données brutes des membres
            
        Returns:
            Liste de membres normalisés
        """
        if not members_data or not isinstance(members_data, list):
            return []
        
        normalized_members = []
        for member in members_data:
            if not isinstance(member, dict):
                continue
            
            # Déterminer le type de membre (label ou label_group)
            if 'label' in member and isinstance(member['label'], dict):
                # C'est un label
                label = member['label']
                label_id = label.get('id')
                if not label_id and 'href' in label:
                    label_id = ApiResponseParser.extract_id_from_href(label['href'])
                
                normalized_member = {
                    'type': 'label',
                    'id': label_id,
                    'href': label.get('href'),
                    'key': label.get('key'),
                    'value': label.get('value'),
                    'display': f"{label.get('key')}:{label.get('value')}" if label.get('key') and label.get('value') else None
                }
                
                normalized_members.append(normalized_member)
                
            elif 'label_group' in member and isinstance(member['label_group'], dict):
                # C'est un groupe de labels
                label_group = member['label_group']
                label_group_id = label_group.get('id')
                if not label_group_id and 'href' in label_group:
                    label_group_id = ApiResponseParser.extract_id_from_href(label_group['href'])
                
                normalized_member = {
                    'type': 'label_group',
                    'id': label_group_id,
                    'href': label_group.get('href'),
                    'name': label_group.get('name')
                }
                
                normalized_members.append(normalized_member)
            
        return normalized_members
    
    @staticmethod
    def get_label_group_info_from_database(db, label_group_id: str) -> Dict[str, Any]:
        """
        Récupère les informations d'un groupe de labels depuis la base de données.
        Cette méthode facilite l'intégration avec _get_entity_details dans export_handler.py.
        
        Args:
            db: Instance de la base de données
            label_group_id: ID du groupe de labels
            
        Returns:
            dict: Informations du groupe de labels ou dictionnaire vide si non trouvé
        """
        if not label_group_id or not db:
            return {}
            
        try:
            # Récupérer le groupe de labels depuis la base de données
            conn, cursor = db.connect()
            
            cursor.execute('''
            SELECT name, description FROM label_groups WHERE id = ?
            ''', (label_group_id,))
            
            row = cursor.fetchone()
            db.close(conn)
            
            if row:
                label_group_data = {
                    'id': label_group_id,
                    'name': row['name'],
                    'description': row.get('description')
                }
                
                # Normaliser les données avec le parseur
                return LabelGroupParser.parse_label_group(label_group_data)
                
            return {}
            
        except Exception as e:
            print(f"Erreur lors de la récupération du groupe de labels {label_group_id}: {e}")
            return {}
    
    @staticmethod
    def get_label_group_display_name(label_group: Optional[Union[Dict[str, Any], str]]) -> str:
        """
        Retourne un nom d'affichage pour un groupe de labels.
        
        Args:
            label_group: Données du groupe de labels ou ID
            
        Returns:
            str: Nom d'affichage du groupe de labels
        """
        if not label_group:
            return "N/A"
            
        if isinstance(label_group, dict):
            # Préférer le nom sur l'ID
            if label_group.get('name'):
                return label_group['name']
            elif label_group.get('id'):
                return f"Groupe {label_group['id']}"
            else:
                return "Groupe de labels inconnu"
        else:
            # Si c'est juste une chaîne, la retourner comme ID
            return f"Groupe {label_group}"
    
    @staticmethod
    def format_label_group_for_display(label_group: Optional[Union[Dict[str, Any], str]]) -> str:
        """
        Formate un groupe de labels pour l'affichage, avec des informations sur les membres si disponibles.
        
        Args:
            label_group: Données du groupe de labels ou ID
            
        Returns:
            str: Représentation formatée du groupe de labels
        """
        if not label_group:
            return "N/A"
            
        if isinstance(label_group, dict):
            group_name = LabelGroupParser.get_label_group_display_name(label_group)
            
            # Ajouter des informations sur les membres si disponibles
            members = label_group.get('members', [])
            if members and isinstance(members, list) and len(members) > 0:
                # Limiter le nombre de membres à afficher
                max_members_to_show = 3
                
                member_descriptions = []
                for i, member in enumerate(members[:max_members_to_show]):
                    if member.get('type') == 'label':
                        if member.get('display'):
                            member_descriptions.append(member['display'])
                        elif member.get('key') and member.get('value'):
                            member_descriptions.append(f"{member['key']}:{member['value']}")
                    elif member.get('type') == 'label_group':
                        if member.get('name'):
                            member_descriptions.append(f"Groupe: {member['name']}")
                
                if len(members) > max_members_to_show:
                    member_descriptions.append(f"... et {len(members) - max_members_to_show} autres membres")
                
                if member_descriptions:
                    return f"{group_name} ({', '.join(member_descriptions)})"
            
            return group_name
        else:
            # Si c'est juste une chaîne, la retourner comme ID
            return f"Groupe {label_group}"