#illumio/models/workload.py
"""
Modèles de données pour les workloads Illumio.

Ce module définit les classes de modèles typés pour représenter
les workloads et leurs composants.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


@dataclass
class Interface:
    """Représente une interface réseau d'un workload."""
    name: str  # ex: 'eth0'
    address: Optional[str] = None
    link_state: str = 'up'
    addresses: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Interface':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls(name='unknown')
        
        # Extraire les adresses supplémentaires
        addresses = []
        if 'addresses' in data:
            if isinstance(data['addresses'], list):
                addresses = [str(addr) for addr in data['addresses'] if addr]
            elif isinstance(data['addresses'], str):
                # Si c'est une chaîne JSON, essayer de la parser
                try:
                    import json
                    addr_list = json.loads(data['addresses'])
                    if isinstance(addr_list, list):
                        addresses = [str(addr) for addr in addr_list if addr]
                except json.JSONDecodeError:
                    pass
        
        return cls(
            name=data.get('name', 'unknown'),
            address=data.get('address'),
            link_state=data.get('link_state', 'up'),
            addresses=addresses
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        result = {
            'name': self.name,
            'link_state': self.link_state
        }
        
        if self.address:
            result['address'] = self.address
            
        if self.addresses:
            result['addresses'] = self.addresses
            
        return result


@dataclass
class WorkloadLabel:
    """Représente un label associé à un workload."""
    key: str
    value: str
    id: Optional[str] = None
    href: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkloadLabel':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls(key='unknown', value='unknown')
        
        # Extraire l'ID si nécessaire
        label_id = data.get('id')
        href = data.get('href')
        if not label_id and href:
            label_id = href.split('/')[-1]
        
        return cls(
            key=data.get('key', 'unknown'),
            value=data.get('value', ''),
            id=label_id,
            href=href
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        result = {
            'key': self.key,
            'value': self.value
        }
        
        if self.href:
            result['href'] = self.href
            
        return result


@dataclass
class Workload:
    """Représente un workload Illumio."""
    id: Optional[str] = None
    href: Optional[str] = None
    name: Optional[str] = None
    hostname: Optional[str] = None
    description: Optional[str] = None
    interfaces: List[Interface] = field(default_factory=list)
    public_ip: Optional[str] = None
    online: bool = True
    enforcement_mode: str = 'visibility_only'
    os_type: Optional[str] = None
    os_detail: Optional[str] = None
    labels: List[WorkloadLabel] = field(default_factory=list)
    service_provider: Optional[str] = None
    data_center: Optional[str] = None
    data_center_zone: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workload':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Extraire l'ID si nécessaire
        workload_id = data.get('id')
        href = data.get('href')
        if not workload_id and href:
            workload_id = href.split('/')[-1]
        
        # Extraire les interfaces
        interfaces_data = data.get('interfaces', [])
        interfaces = [Interface.from_dict(iface) for iface in interfaces_data if isinstance(iface, dict)]
        
        # Extraire les labels
        labels_data = data.get('labels', [])
        labels = [WorkloadLabel.from_dict(label) for label in labels_data if isinstance(label, dict)]
        
        # Traiter enforcement_mode qui peut être un objet ou une chaîne
        enforcement_mode = data.get('enforcement_mode', 'visibility_only')
        if isinstance(enforcement_mode, dict) and 'mode' in enforcement_mode:
            enforcement_mode = enforcement_mode['mode']
        
        # Créer l'instance
        return cls(
            id=workload_id,
            href=href,
            name=data.get('name'),
            hostname=data.get('hostname'),
            description=data.get('description'),
            interfaces=interfaces,
            public_ip=data.get('public_ip'),
            online=bool(data.get('online', True)),
            enforcement_mode=enforcement_mode,
            os_type=data.get('os_type'),
            os_detail=data.get('os_detail'),
            labels=labels,
            service_provider=data.get('service_provider'),
            data_center=data.get('data_center'),
            data_center_zone=data.get('data_center_zone')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        result = {}
        
        # Ajouter les champs simples seulement s'ils existent
        for field in ['name', 'hostname', 'description', 'public_ip', 'os_type', 
                     'os_detail', 'service_provider', 'data_center', 'data_center_zone']:
            if hasattr(self, field) and getattr(self, field):
                result[field] = getattr(self, field)
        
        # Ajouter les champs booléens
        result['online'] = self.online
        
        # Ajouter le mode d'enforcement
        result['enforcement_mode'] = self.enforcement_mode
        
        # Ajouter les interfaces
        if self.interfaces:
            result['interfaces'] = [iface.to_dict() for iface in self.interfaces]
            
        # Ajouter les labels
        if self.labels:
            result['labels'] = [label.to_dict() for label in self.labels]
            
        # Ajouter l'ID et le href si présents
        if self.id:
            result['id'] = self.id
            
        if self.href:
            result['href'] = self.href
            
        return result
    
    def get_ip_addresses(self) -> List[str]:
        """Récupère toutes les adresses IP du workload."""
        addresses = []
        
        # Ajouter l'IP publique si elle existe
        if self.public_ip:
            addresses.append(self.public_ip)
        
        # Ajouter les adresses des interfaces
        for interface in self.interfaces:
            if interface.address:
                addresses.append(interface.address)
            addresses.extend(interface.addresses)
        
        # Éliminer les doublons
        return list(set(addresses))
    
    def find_label_by_key(self, key: str) -> Optional[WorkloadLabel]:
        """Trouve un label par sa clé."""
        for label in self.labels:
            if label.key == key:
                return label
        return None