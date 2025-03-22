# illumio/models/label_group.py
"""
Modèles de données pour les groupes de labels Illumio.

Ce module définit les classes de modèles typés pour représenter
les groupes de labels et leurs membres.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union

from .label import Label


@dataclass
class LabelGroupMember:
    """Représente un membre d'un groupe de labels."""
    id: Optional[str] = None
    href: Optional[str] = None
    name: Optional[str] = None
    type: str = 'label'  # 'label' ou 'label_group'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LabelGroupMember':
        """
        Crée une instance de LabelGroupMember à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du membre
            
        Returns:
            Instance de LabelGroupMember
        """
        if not data:
            return cls()
        
        # Déterminer le type de membre
        member_type = 'label'
        if 'label_group' in data:
            member_type = 'label_group'
        
        # Extraire l'ID et le href en fonction du type
        member_id = None
        href = None
        name = None
        
        if member_type == 'label' and 'label' in data:
            label_data = data['label']
            href = label_data.get('href')
            member_id = href.split('/')[-1] if href else None
            name = f"{label_data.get('key')}:{label_data.get('value')}" if 'key' in label_data else None
        elif member_type == 'label_group' and 'label_group' in data:
            label_group_data = data['label_group']
            href = label_group_data.get('href')
            member_id = href.split('/')[-1] if href else None
            name = label_group_data.get('name')
        
        return cls(
            id=member_id,
            href=href,
            name=name,
            type=member_type
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant le membre du groupe
        """
        if self.type == 'label':
            # Format pour référencer un label
            return {
                'label': {
                    'href': self.href
                }
            }
        elif self.type == 'label_group':
            # Format pour référencer un groupe de labels
            return {
                'label_group': {
                    'href': self.href
                }
            }
        
        # Cas par défaut
        return {
            'id': self.id,
            'href': self.href,
            'name': self.name,
            'type': self.type
        }


@dataclass
class LabelGroup:
    """Représente un groupe de labels Illumio."""
    name: str
    id: Optional[str] = None
    href: Optional[str] = None
    description: Optional[str] = None
    members: List[LabelGroupMember] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LabelGroup':
        """
        Crée une instance de LabelGroup à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du groupe de labels
            
        Returns:
            Instance de LabelGroup
        
        Raises:
            ValueError: Si des données obligatoires sont manquantes
        """
        if not data:
            raise ValueError("Données de groupe de labels manquantes")
        
        # Extraire l'ID à partir du href si nécessaire
        group_id = data.get('id')
        href = data.get('href')
        if not group_id and href:
            group_id = href.split('/')[-1]
        
        # Vérifier le nom
        name = data.get('name')
        if not name:
            raise ValueError("Nom de groupe de labels manquant")
        
        # Extraire les membres
        members = []
        
        # Les membres peuvent être dans 'sub_groups', 'labels' ou d'autres champs
        for member_list_key in ['sub_groups', 'labels', 'members']:
            member_list = data.get(member_list_key, [])
            for member_data in member_list:
                if isinstance(member_data, dict):
                    members.append(LabelGroupMember.from_dict(member_data))
        
        return cls(
            name=name,
            id=group_id,
            href=href,
            description=data.get('description'),
            members=members,
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant le groupe de labels
        """
        result = {
            'name': self.name
        }
        
        # Ajouter les champs optionnels s'ils existent
        if self.id:
            result['id'] = self.id
        
        if self.href:
            result['href'] = self.href
        
        if self.description:
            result['description'] = self.description
        
        if self.created_at:
            result['created_at'] = self.created_at
        
        if self.updated_at:
            result['updated_at'] = self.updated_at
        
        # Convertir les membres si présents
        if self.members:
            result['members'] = [member.to_dict() for member in self.members]
        
        return result
    
    def add_label(self, label: Union[Label, str, Dict[str, Any]]) -> None:
        """
        Ajoute un label au groupe.
        
        Args:
            label: Label à ajouter (instance de Label, chaîne d'ID ou dictionnaire)
        
        Raises:
            ValueError: Si le label n'est pas valide
        """
        # Traitement selon le type de l'argument
        if isinstance(label, Label):
            # Cas où c'est une instance de Label
            if not label.href:
                raise ValueError("Le label doit avoir un href pour être ajouté à un groupe")
            
            member = LabelGroupMember(
                id=label.id,
                href=label.href,
                name=f"{label.key}:{label.value}",
                type='label'
            )
        elif isinstance(label, str):
            # Cas où c'est un ID ou href de label
            if '/' in label:
                # C'est probablement un href
                href = label
                label_id = href.split('/')[-1]
            else:
                # C'est probablement un ID
                label_id = label
                href = f"/api/v2/orgs/1/labels/{label_id}"
            
            member = LabelGroupMember(
                id=label_id,
                href=href,
                type='label'
            )
        elif isinstance(label, dict):
            # Cas où c'est un dictionnaire
            member = LabelGroupMember.from_dict({'label': label})
        else:
            raise ValueError(f"Type de label non pris en charge: {type(label)}")
        
        # Ajouter le membre s'il n'existe pas déjà
        if not any(m.href == member.href for m in self.members):
            self.members.append(member)
    
    def add_label_group(self, group: Union['LabelGroup', str, Dict[str, Any]]) -> None:
        """
        Ajoute un sous-groupe au groupe.
        
        Args:
            group: Groupe à ajouter (instance de LabelGroup, chaîne d'ID ou dictionnaire)
        
        Raises:
            ValueError: Si le groupe n'est pas valide
        """
        # Traitement selon le type de l'argument
        if isinstance(group, LabelGroup):
            # Cas où c'est une instance de LabelGroup
            if not group.href:
                raise ValueError("Le groupe doit avoir un href pour être ajouté comme sous-groupe")
            
            member = LabelGroupMember(
                id=group.id,
                href=group.href,
                name=group.name,
                type='label_group'
            )
        elif isinstance(group, str):
            # Cas où c'est un ID ou href de groupe
            if '/' in group:
                # C'est probablement un href
                href = group
                group_id = href.split('/')[-1]
            else:
                # C'est probablement un ID
                group_id = group
                href = f"/api/v2/orgs/1/label_groups/{group_id}"
            
            member = LabelGroupMember(
                id=group_id,
                href=href,
                type='label_group'
            )
        elif isinstance(group, dict):
            # Cas où c'est un dictionnaire
            member = LabelGroupMember.from_dict({'label_group': group})
        else:
            raise ValueError(f"Type de groupe non pris en charge: {type(group)}")
        
        # Ajouter le membre s'il n'existe pas déjà
        if not any(m.href == member.href for m in self.members):
            self.members.append(member)